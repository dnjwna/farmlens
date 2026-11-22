from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.models.farmer import Farmer, Farm, InsurancePolicy
from app.schemas.farmer import (
    FarmerRegister, FarmerLogin, Token,
    FarmerResponse, FarmCreate, FarmResponse,
    FarmerUpdate, PasswordChange, AccountDelete,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services.auth_service import (
    register_farmer, login_farmer, update_farmer, change_password, delete_account, issue_token,
)
from app.services import password_reset_service
from app.services.diagnosis_service import delete_stored_images

router = APIRouter(prefix="/auth", tags=["Authentication"])
farm_router = APIRouter(prefix="/farms", tags=["Farms"])
bearer_scheme = HTTPBearer()

def get_current_farmer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Farmer:
    try:
        payload = decode_token(credentials.credentials)
        farmer_id = UUID(str(payload.get("sub")))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token expired atau tidak valid")

    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=401, detail="Akun tidak ditemukan. Silakan masuk lagi.")
    # Tokens issued before a password change/reset carry an older version.
    if payload.get("ver", 0) != (farmer.token_version or 0):
        raise HTTPException(status_code=401, detail="Sesi berakhir karena password diganti. Silakan masuk lagi.")
    return farmer


@router.post("/register", response_model=FarmerResponse, status_code=201)
def register(data: FarmerRegister, db: Session = Depends(get_db)):
    return register_farmer(db, data)

@router.post("/login", response_model=Token)
def login(data: FarmerLogin, db: Session = Depends(get_db)):
    return login_farmer(db, data)

@router.get("/me", response_model=FarmerResponse)
def get_profile(farmer: Farmer = Depends(get_current_farmer)):
    return farmer


@router.patch("/me", response_model=FarmerResponse)
def update_profile(
    data: FarmerUpdate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    return update_farmer(db, farmer, data)


@router.post("/change-password", response_model=Token)
def change_my_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    """Returns a new token: other devices are logged out, this one stays signed in."""
    return change_password(db, farmer, data)


FORGOT_PASSWORD_MESSAGE = (
    "Jika nomor ini terdaftar, kode reset sudah dikirim lewat WhatsApp. "
    "Kode berlaku 10 menit."
)


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Same response whether or not the number is registered, so it cannot be used to probe accounts."""
    result = password_reset_service.request_reset(db, data.phone_number)
    if result is not None:
        canonical, code = result
        background_tasks.add_task(password_reset_service.deliver_code, canonical, code)
    return {"detail": FORGOT_PASSWORD_MESSAGE}


@router.post("/reset-password", response_model=Token)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """On success all existing sessions are logged out and the caller is signed in."""
    farmer = password_reset_service.reset_password(db, data.phone_number, data.code, data.new_password)
    return issue_token(farmer)


@router.post("/delete-account", status_code=204)
def delete_my_account(
    data: AccountDelete,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    image_urls = delete_account(db, farmer, data.password)
    delete_stored_images(image_urls)


@farm_router.post("/", response_model=FarmResponse, status_code=201)
def add_farm(
    data: FarmCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    farm = Farm(**data.model_dump(), farmer_id=farmer.id)
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm

@farm_router.get("/", response_model=list[FarmResponse])
def list_farms(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    return (
        db.query(Farm)
        .filter(Farm.farmer_id == farmer.id, Farm.deleted_at.is_(None))
        .order_by(Farm.created_at)
        .all()
    )


@farm_router.delete("/{farm_id}", status_code=204)
def delete_farm(
    farm_id: UUID,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    farm = db.query(Farm).filter(
        Farm.id == farm_id, Farm.farmer_id == farmer.id, Farm.deleted_at.is_(None)
    ).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Lahan tidak ditemukan")

    has_active_policy = db.query(InsurancePolicy).filter(
        InsurancePolicy.farm_id == farm.id, InsurancePolicy.status == "active"
    ).first()
    if has_active_policy:
        raise HTTPException(
            status_code=409,
            detail="Lahan ini masih punya polis asuransi aktif, jadi belum bisa dihapus.",
        )

    farm.deleted_at = datetime.utcnow()
    db.commit()