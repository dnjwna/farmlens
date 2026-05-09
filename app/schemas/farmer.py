from pydantic import BaseModel, validator
from uuid import UUID
from datetime import datetime
from typing import Optional


class FarmerRegister(BaseModel):
    full_name: str
    phone_number: str
    password: str
    province: Optional[str] = None
    city: Optional[str] = None

    @validator('phone_number')
    def phone_must_be_valid(cls, v):
        if not (v.startswith('08') or v.startswith('+62')):
            raise ValueError('Nomor HP harus diawali 08 atau +62')
        return v

    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password minimal 8 karakter')
        return v


class FarmerLogin(BaseModel):
    phone_number: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FarmerResponse(BaseModel):
    id: UUID
    full_name: str
    phone_number: str
    province: Optional[str]
    city: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FarmCreate(BaseModel):
    name: str
    area_hectares: float
    crop_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FarmResponse(FarmCreate):
    id: UUID
    farmer_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class DiagnosisCreate(BaseModel):
    farm_id: UUID


class DiagnosisResponse(BaseModel):
    id: UUID
    farmer_id: UUID
    farm_id: UUID
    image_url: str
    disease_name: Optional[str]
    confidence_score: Optional[float]
    recommendation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True