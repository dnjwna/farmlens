"""
Forgot-password flow.

Security properties:
- The response to a reset request never reveals whether a number is registered.
- Codes are 6 random digits, stored only as an HMAC (keyed with SECRET_KEY), single use,
  valid OTP_TTL_MINUTES, and locked after MAX_ATTEMPTS wrong guesses.
- At most MAX_REQUESTS_PER_HOUR requests per number, registered or not (limits OTP spam cost).
- A successful reset increments token_version, which logs out every existing session.
"""
import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.farmer import Farmer, PasswordResetCode
from app.services.otp_sender import send_reset_code

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = 10
ADMIN_CODE_TTL_MINUTES = 24 * 60
MAX_ATTEMPTS = 5
MAX_REQUESTS_PER_HOUR = 3

INVALID_CODE = "Kode salah atau sudah kedaluwarsa. Minta kode baru."


def canonical_phone(raw: str) -> Optional[str]:
    """'0812-3456 7890' / '+62812...' / '62812...' -> '62812...'. None if not an Indonesian mobile number."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    if not re.fullmatch(r"628\d{7,12}", digits):
        return None
    return digits


def stored_phone_variants(canonical: str) -> list[str]:
    """Numbers were stored as typed at registration (08..., +62..., 62...)."""
    local = canonical[2:]
    return [f"0{local}", f"+62{local}", f"62{local}"]


def find_farmer_by_phone(db: Session, canonical: str) -> Optional[Farmer]:
    return db.query(Farmer).filter(Farmer.phone_number.in_(stored_phone_variants(canonical))).first()


def _hash_code(code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def _new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _invalidate_open_codes(db: Session, canonical: str) -> None:
    now = datetime.utcnow()
    db.query(PasswordResetCode).filter(
        PasswordResetCode.phone_number == canonical,
        PasswordResetCode.used_at.is_(None),
    ).update({PasswordResetCode.used_at: now}, synchronize_session=False)


def request_reset(db: Session, raw_phone: str) -> Optional[tuple[str, str]]:
    """
    Record a reset request. Returns (canonical_phone, code) when a code must be sent,
    None when the number is not registered. Raises 429 when rate limited.
    The caller sends the code in the background so response time does not leak existence.
    """
    canonical = canonical_phone(raw_phone)
    if canonical is None:
        raise HTTPException(status_code=422, detail="Masukkan nomor HP yang diawali 08 atau +62.")

    hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent = db.query(PasswordResetCode).filter(
        PasswordResetCode.phone_number == canonical,
        PasswordResetCode.source == "otp",
        PasswordResetCode.created_at >= hour_ago,
    ).count()
    if recent >= MAX_REQUESTS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Terlalu banyak permintaan kode. Coba lagi dalam 1 jam.")

    farmer = find_farmer_by_phone(db, canonical)
    now = datetime.utcnow()
    if farmer is None:
        db.add(PasswordResetCode(phone_number=canonical, expires_at=now, used_at=now))  # rate-limit marker only
        db.commit()
        return None

    _invalidate_open_codes(db, canonical)
    code = _new_code()
    db.add(
        PasswordResetCode(
            phone_number=canonical,
            farmer_id=farmer.id,
            code_hash=_hash_code(code),
            source="otp",
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        )
    )
    db.commit()
    return canonical, code


async def deliver_code(canonical: str, code: str) -> None:
    """Background task: delivery failures are logged, never shown to the requester."""
    try:
        await send_reset_code(canonical, code, OTP_TTL_MINUTES)
    except Exception as exc:  # noqa: BLE001 - any delivery failure must stay server-side
        logger.error("Failed to deliver reset code to %s****: %s", canonical[:4], exc)


def reset_password(db: Session, raw_phone: str, code: str, new_password: str) -> Farmer:
    canonical = canonical_phone(raw_phone)
    if canonical is None:
        raise HTTPException(status_code=400, detail=INVALID_CODE)

    now = datetime.utcnow()
    entry = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.phone_number == canonical,
            PasswordResetCode.farmer_id.isnot(None),
            PasswordResetCode.used_at.is_(None),
            PasswordResetCode.expires_at > now,
        )
        .order_by(PasswordResetCode.created_at.desc())
        .first()
    )
    if entry is None:
        raise HTTPException(status_code=400, detail=INVALID_CODE)

    if not hmac.compare_digest(entry.code_hash or "", _hash_code(code.strip())):
        entry.attempts += 1
        remaining = MAX_ATTEMPTS - entry.attempts
        if remaining <= 0:
            entry.used_at = now  # locked: a new code must be requested
            db.commit()
            raise HTTPException(status_code=400, detail="Terlalu banyak percobaan salah. Minta kode baru.")
        db.commit()
        raise HTTPException(status_code=400, detail=f"Kode salah. Sisa {remaining} percobaan.")

    farmer = db.get(Farmer, entry.farmer_id)
    if farmer is None:
        raise HTTPException(status_code=400, detail=INVALID_CODE)

    farmer.password_hash = hash_password(new_password)
    farmer.token_version = (farmer.token_version or 0) + 1  # log out all existing sessions
    entry.used_at = now
    _invalidate_open_codes(db, canonical)
    db.commit()
    db.refresh(farmer)
    return farmer


def issue_admin_code(db: Session, raw_phone: str) -> tuple[Farmer, str]:
    """For assisted recovery: an officer verifies the farmer in person and hands over this code."""
    canonical = canonical_phone(raw_phone)
    farmer = find_farmer_by_phone(db, canonical) if canonical else None
    if farmer is None:
        raise HTTPException(status_code=404, detail="Nomor HP tidak terdaftar")
    _invalidate_open_codes(db, canonical)
    code = _new_code()
    db.add(
        PasswordResetCode(
            phone_number=canonical,
            farmer_id=farmer.id,
            code_hash=_hash_code(code),
            source="admin",
            expires_at=datetime.utcnow() + timedelta(minutes=ADMIN_CODE_TTL_MINUTES),
        )
    )
    db.commit()
    return farmer, code
