from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.api.auth import get_current_farmer
from app.models.farmer import Farmer, Diagnosis, Farm
from app.schemas.farmer import DiagnosisResponse
from app.services.diagnosis_service import diagnose_plant

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
    # Validasi farm milik petani yang login
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.farmer_id == farmer.id
    ).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Lahan tidak ditemukan")

    # Validasi tipe file
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Format file harus JPG, PNG, atau WebP"
        )

    # Baca dan validasi ukuran file
    image_bytes = await file.read()
    if len(image_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file maksimal {MAX_SIZE_MB}MB"
        )

    # Kirim ke Gemini untuk diagnosis
    result = await diagnose_plant(image_bytes)

    # Simpan hasil ke database
    diagnosis = Diagnosis(
        farmer_id=farmer.id,
        farm_id=farm_id,
        image_url=f"uploaded/{file.filename}",  # nanti diganti Supabase Storage
        disease_name=result.get("disease_name"),
        confidence_score=result.get("confidence_score"),
        recommendation=f"{result.get('recommendation', '')} | Pencegahan: {result.get('preventive_measures', '')}"
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.get("/", response_model=list[DiagnosisResponse])
def list_diagnoses(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    return db.query(Diagnosis).filter(
        Diagnosis.farmer_id == farmer.id
    ).order_by(Diagnosis.created_at.desc()).all()


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