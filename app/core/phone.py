"""
Single source of truth for Indonesian mobile numbers.

Stored format (E.164): "+6281234567890".
Accepted input: "081234567890", "+62 812-3456-7890", "6281234567890", "(0812) 3456 7890".
"""
import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 628 + 7..11 digits  ->  9..13 digits in local 08... form
_CANONICAL_DIGITS = re.compile(r"628\d{7,11}")

INVALID_PHONE_MESSAGE = "Nomor HP tidak valid. Gunakan nomor yang diawali 08 atau +62."


def phone_digits(raw: Optional[str]) -> Optional[str]:
    """'0812-3456 7890' -> '6281234567890' (no plus). None if not an Indonesian mobile number."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    return digits if _CANONICAL_DIGITS.fullmatch(digits) else None


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Stored format, e.g. '+6281234567890'. None if invalid."""
    digits = phone_digits(raw)
    return f"+{digits}" if digits else None


def lookup_variants(raw: Optional[str]) -> list[str]:
    """
    Values that may identify this number in the farmers table. After the one-time
    migration only the canonical form exists; the legacy forms cover rows that could
    not be migrated (see normalize_existing_phone_numbers).
    """
    digits = phone_digits(raw)
    if not digits:
        return []
    local = digits[2:]
    return [f"+62{local}", f"0{local}", f"62{local}"]


def normalize_existing_phone_numbers(db: Session) -> dict:
    """
    Idempotent migration of legacy rows to the canonical format.
    Never merges accounts: if two rows are the same number in different formats,
    both are left untouched and logged for manual review.
    """
    from app.models.farmer import Farmer

    rows = db.query(Farmer.id, Farmer.phone_number).all()
    by_canonical: dict[str, list] = {}
    invalid = []
    for farmer_id, phone in rows:
        canonical = normalize_phone(phone)
        if canonical is None:
            invalid.append(phone)
            continue
        by_canonical.setdefault(canonical, []).append((farmer_id, phone))

    updated, conflicts = 0, []
    for canonical, owners in by_canonical.items():
        if len(owners) > 1:
            conflicts.append([phone for _, phone in owners])
            continue
        farmer_id, phone = owners[0]
        if phone != canonical:
            db.query(Farmer).filter(Farmer.id == farmer_id).update({Farmer.phone_number: canonical})
            updated += 1
    db.commit()

    if conflicts:
        logger.warning("Phone migration: %d duplicate numbers need manual review: %s", len(conflicts), conflicts)
    if invalid:
        logger.warning("Phone migration: %d invalid numbers left unchanged", len(invalid))
    if updated:
        logger.info("Phone migration: %d numbers normalized", updated)
    return {"updated": updated, "conflicts": conflicts, "invalid": len(invalid)}
