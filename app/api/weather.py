from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.api.auth import get_current_farmer
from app.models.farmer import Farmer, Farm
from app.services.weather_service import get_weather

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/farm/{farm_id}")
async def get_farm_weather(
    farm_id: UUID,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer)
):
    # Ambil data lahan
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.farmer_id == farmer.id
    ).first()

    if not farm:
        raise HTTPException(status_code=404, detail="Lahan tidak ditemukan")

    if not farm.latitude or not farm.longitude:
        raise HTTPException(
            status_code=400,
            detail="Lahan belum memiliki koordinat. Update koordinat lahan terlebih dahulu."
        )

    try:
        weather_data = await get_weather(farm.latitude, farm.longitude)
        return {
            "farm_name": farm.name,
            "crop_type": farm.crop_type,
            "location": {
                "latitude": farm.latitude,
                "longitude": farm.longitude,
            },
            **weather_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Gagal mengambil data cuaca: {str(e)}"
        )


@router.get("/location")
async def get_weather_by_location(
    latitude: float,
    longitude: float,
    farmer: Farmer = Depends(get_current_farmer)
):
    """Ambil cuaca berdasarkan koordinat langsung (tanpa farm_id)."""
    try:
        return await get_weather(latitude, longitude)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Gagal mengambil data cuaca: {str(e)}"
        )