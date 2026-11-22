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

    return issue_token(farmer)


def issue_token(farmer: Farmer) -> dict:
    """The "ver" claim ties the token to the farmer's current token_version."""
    token = create_access_token(data={"sub": str(farmer.id), "ver": farmer.token_version or 0})
    return {"access_token": token, "token_type": "bearer"}

# ---------------------------------------------------------------------------
# Profile management
# ---------------------------------------------------------------------------

from app.models.farmer import Diagnosis, Farm, InsuranceClaim, InsurancePolicy  # noqa: E402
from app.schemas.farmer import FarmerUpdate, PasswordChange  # noqa: E402


def update_farmer(db: Session, farmer: Farmer, data: FarmerUpdate) -> Farmer:
    changes = data.model_dump(exclude_unset=True)
    if "full_name" in changes and changes["full_name"] is None:
        changes.pop("full_name")  # name is required; ignore explicit null
    for field, value in changes.items():
        setattr(farmer, field, value)
    db.commit()
    db.refresh(farmer)
    return farmer


def change_password(db: Session, farmer: Farmer, data: PasswordChange) -> dict:
    """Changes the password, logs out every other session, returns a fresh token for this one."""
    if not verify_password(data.current_password, farmer.password_hash):
        raise HTTPException(status_code=400, detail="Password lama salah")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="Password baru harus berbeda dari yang lama")
    farmer.password_hash = hash_password(data.new_password)
    farmer.token_version = (farmer.token_version or 0) + 1
    db.commit()
    db.refresh(farmer)
    return issue_token(farmer)


def delete_account(db: Session, farmer: Farmer, password: str) -> list[str]:
    """
    Permanently delete the farmer and everything that belongs to them
    (claims, policies, diagnoses, farms). Returns stored image URLs so the
    caller can remove the photos from storage after the DB commit succeeds.
    """
    if not verify_password(password, farmer.password_hash):
        raise HTTPException(status_code=400, detail="Password salah")

    image_urls = [
        url for (url,) in db.query(Diagnosis.image_url).filter(Diagnosis.farmer_id == farmer.id).all() if url
    ]
    policy_ids = [pid for (pid,) in db.query(InsurancePolicy.id).filter(InsurancePolicy.farmer_id == farmer.id).all()]

    # Children first, so foreign keys never point at a deleted row.
    db.query(InsuranceClaim).filter(
        (InsuranceClaim.farmer_id == farmer.id) | (InsuranceClaim.policy_id.in_(policy_ids))
    ).delete(synchronize_session=False)
    db.query(InsurancePolicy).filter(InsurancePolicy.farmer_id == farmer.id).delete(synchronize_session=False)
    db.query(Diagnosis).filter(Diagnosis.farmer_id == farmer.id).delete(synchronize_session=False)
    db.query(Farm).filter(Farm.farmer_id == farmer.id).delete(synchronize_session=False)
    db.query(Farmer).filter(Farmer.id == farmer.id).delete(synchronize_session=False)
    db.commit()
    return image_urls
