from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.models.farmer import Farmer, Farm, InsurancePolicy
from app.schemas.farmer import (
    FarmerRegister, FarmerLogin, Token,
    FarmerResponse, FarmCreate, FarmResponse
)
from app.services.auth_service import register_farmer, login_farmer

router = APIRouter(prefix="/auth", tags=["Authentication"])
farm_router = APIRouter(prefix="/farms", tags=["Farms"])
bearer_scheme = HTTPBearer()

def get_current_farmer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Farmer:
    try:
        payload = decode_token(credentials.credentials)
        farmer_id = payload.get("sub")
        if not farmer_id:
            raise HTTPException(status_code=401, detail="Token tidak valid")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired atau tidak valid")

    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Petani tidak ditemukan")
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