from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.api.auth import get_current_farmer
from app.models.farmer import Farmer, InsurancePolicy, InsuranceClaim
from app.schemas.farmer import PolicyCreate, PolicyResponse, ClaimResponse
from app.services.insurance_service import create_policy, check_and_trigger_claims

router = APIRouter(prefix="/insurance", tags=["Insurance"])


@router.post("/policies", response_model=PolicyResponse, status_code=201)
def create_insurance_policy(
    data: PolicyCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    return create_policy(db, farmer.id, data)


@router.get("/policies", response_model=list[PolicyResponse])
def list_policies(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    return db.query(InsurancePolicy).filter(
        InsurancePolicy.farmer_id == farmer.id
    ).order_by(InsurancePolicy.created_at.desc()).all()


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    policy = db.query(InsurancePolicy).filter(
        InsurancePolicy.id == policy_id,
        InsurancePolicy.farmer_id == farmer.id
    ).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Polis tidak ditemukan")
    return policy


@router.get("/claims", response_model=list[ClaimResponse])
def list_claims(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    return db.query(InsuranceClaim).filter(
        InsuranceClaim.farmer_id == farmer.id
    ).order_by(InsuranceClaim.created_at.desc()).all()


@router.post("/check-triggers")
async def manual_check_triggers(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    """
    Trigger manual untuk test — di production ini dipanggil scheduler otomatis tiap hari.
    """
    claims = await check_and_trigger_claims(db)
    return {
        "message": f"{len(claims)} klaim baru dibuat",
        "claims_created": len(claims)
    }