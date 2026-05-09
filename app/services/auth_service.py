from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.farmer import Farmer
from app.schemas.farmer import FarmerRegister, FarmerLogin
from app.core.security import hash_password, verify_password, create_access_token

def register_farmer(db: Session, data: FarmerRegister) -> Farmer:
    existing = db.query(Farmer).filter(
        Farmer.phone_number == data.phone_number
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nomor HP sudah terdaftar"
        )

    farmer = Farmer(
        full_name=data.full_name,
        phone_number=data.phone_number,
        password_hash=hash_password(data.password),
        province=data.province,
        city=data.city,
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer

def login_farmer(db: Session, data: FarmerLogin) -> dict:
    farmer = db.query(Farmer).filter(
        Farmer.phone_number == data.phone_number
    ).first()

    if not farmer or not verify_password(data.password, farmer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nomor HP atau password salah"
        )

    token = create_access_token(data={"sub": str(farmer.id)})
    return {"access_token": token, "token_type": "bearer"}