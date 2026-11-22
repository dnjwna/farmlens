"""
Admin-only endpoints, protected by the X-Admin-Key header.
Not used by the farmer app. Intended for an external cron job or manual operations.
"""
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.farmer import AdminResetRequest
from app.services.insurance_service import run_daily_insurance_check
from app.services.password_reset_service import ADMIN_CODE_TTL_MINUTES, issue_admin_code


def require_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Endpoint admin belum dikonfigurasi (ADMIN_API_KEY kosong)")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Admin key tidak valid")


router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.post("/insurance/run-daily-check")
async def run_daily_check(db: Session = Depends(get_db)):
    """
    Evaluate all active policies against yesterday's weather and create claims.
    Idempotent: calling it again the same day does not create duplicate claims.
    """
    return await run_daily_insurance_check(db)


@router.post("/users/reset-password")
def admin_reset_password(data: AdminResetRequest, db: Session = Depends(get_db)):
    """
    Assisted recovery when WhatsApp delivery fails. An officer verifies the farmer
    in person, then hands over this code; the farmer enters it on the reset page.
    """
    farmer, code = issue_admin_code(db, data.phone_number)
    return {
        "full_name": farmer.full_name,
        "code": code,
        "valid_hours": ADMIN_CODE_TTL_MINUTES // 60,
    }
