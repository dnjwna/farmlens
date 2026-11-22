import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from app.core.database import get_db
from app.api.auth import get_current_farmer
from app.models.farmer import Farmer, Diagnosis, Farm
from app.schemas.farmer import DiagnosisResponse
from app.services.diagnosis_service import DiagnosisError, diagnose_plant
from app.services.weather_service import get_recent_weather_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/diagnoses", tags=["Diagnosis"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB = 10

@router.post("/", response_model=DiagnosisResponse, status_code=201)
async def create_diagnosis(
    farm_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.farmer_id == farmer.id,
        Farm.deleted_at.is_(None),
    ).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Lahan tidak ditemukan")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Format file harus JPG, PNG, atau WebP")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Ukuran file maksimal {MAX_SIZE_MB}MB")

    # Recent weather is supporting context only; diagnosis proceeds without it.
    weather_context = None
    if farm.latitude is not None and farm.longitude is not None:
        try:
            weather_context = await get_recent_weather_context(farm.latitude, farm.longitude)
        except Exception as exc:
            logger.warning("Weather context unavailable, diagnosing without it: %s", exc)

    try:
        result = await diagnose_plant(
            image_bytes,
            filename=file.filename or "image.jpg",
            mime_type=file.content_type,
            crop_type=farm.crop_type,
            weather_context=weather_context,
        )
    except DiagnosisError as exc:
        logger.error("Diagnosis failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Layanan AI sedang tidak tersedia. Coba lagi beberapa saat lagi.",
        )

    diagnosis = Diagnosis(
        farmer_id=farmer.id,
        farm_id=farm_id,
        image_url=result.get("image_url", ""),
        disease_name=result.get("disease_name"),
        confidence_score=result.get("confidence_score"),
        severity=result.get("severity"),
        cause_explanation=result.get("cause_explanation"),
        warning_signs=result.get("warning_signs"),
        action_steps=result.get("action_steps"),
        urgency=result.get("urgency"),
        estimated_yield_impact=result.get("estimated_yield_impact"),
        recommendation=result.get("preventive_measures"),
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.get("/", response_model=list[DiagnosisResponse])
def list_diagnoses(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    return (
        db.query(Diagnosis)
        .options(joinedload(Diagnosis.farm))
        .filter(Diagnosis.farmer_id == farmer.id)
        .order_by(Diagnosis.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{diagnosis_id}", response_model=DiagnosisResponse)
def get_diagnosis(
    diagnosis_id: UUID,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    diagnosis = db.query(Diagnosis).filter(
        Diagnosis.id == diagnosis_id,
        Diagnosis.farmer_id == farmer.id
    ).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis tidak ditemukan")
    return diagnosis