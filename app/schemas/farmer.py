from pydantic import BaseModel, Field, field_validator, validator
from uuid import UUID
from datetime import datetime
from typing import Optional
from datetime import date
from typing import Optional, List


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
    farm_name: Optional[str] = None
    farmer_id: UUID
    farm_id: UUID
    image_url: str
    disease_name: Optional[str]
    confidence_score: Optional[float]
    severity: Optional[str]
    cause_explanation: Optional[str]
    warning_signs: Optional[str]
    action_steps: Optional[str]
    urgency: Optional[str]
    estimated_yield_impact: Optional[str]
    recommendation: Optional[str]
    created_at: datetime

class PolicyCreate(BaseModel):
    farm_id: UUID
    premium_amount: float
    coverage_amount: float
    duration_months: int = 6
    trigger_rain_mm: float = 50.0
    trigger_dry_days: float = 7.0
    trigger_temp_max: float = 38.0

class PolicyResponse(BaseModel):
    id: UUID
    farmer_id: UUID
    farm_id: UUID
    status: str
    premium_amount: float
    coverage_amount: float
    start_date: datetime
    end_date: datetime
    trigger_rain_mm: float
    trigger_dry_days: float
    trigger_temp_max: float
    created_at: datetime

    class Config:
        from_attributes = True

class ClaimResponse(BaseModel):
    id: UUID
    policy_id: UUID
    farmer_id: UUID
    trigger_type: str
    trigger_value: float
    trigger_threshold: float
    claim_amount: float
    status: str
    weather_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class FarmerUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=100)
    province: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError("Nama minimal 2 karakter")
        return v.strip() if v is not None else v

    @field_validator("province", "city")
    @classmethod
    def strip_or_none(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password baru minimal 8 karakter")
        return v


class ForgotPasswordRequest(BaseModel):
    phone_number: str


class ResetPasswordRequest(BaseModel):
    phone_number: str
    code: str
    new_password: str

    @field_validator("code")
    @classmethod
    def code_format(cls, v):
        v = v.strip()
        if not (len(v) == 6 and v.isdigit()):
            raise ValueError("Kode terdiri dari 6 angka")
        return v

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password baru minimal 8 karakter")
        return v


class AdminResetRequest(BaseModel):
    phone_number: str


class AccountDelete(BaseModel):
    password: str
