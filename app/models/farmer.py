import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    province = Column(String(100))
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    farms = relationship("Farm", back_populates="farmer")
    diagnoses = relationship("Diagnosis", back_populates="farmer")


class Farm(Base):
    __tablename__ = "farms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False)
    name = Column(String(100), nullable=False)
    area_hectares = Column(Float, nullable=False)
    crop_type = Column(String(50), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="farms")
    diagnoses = relationship("Diagnosis", back_populates="farm")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)
    image_url = Column(String, nullable=False)
    disease_name = Column(String(100))
    confidence_score = Column(Float)
    recommendation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="diagnoses")
    farm = relationship("Farm", back_populates="diagnoses")

class InsurancePolicy(Base):
    __tablename__ = "insurance_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False)
    farm_id = Column(UUID(as_uuid=True), ForeignKey("farms.id"), nullable=False)
    status = Column(String(20), default="active")  # active, expired, cancelled
    premium_amount = Column(Float, nullable=False)  # premi per bulan (IDR)
    coverage_amount = Column(Float, nullable=False)  # maksimal klaim (IDR)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # Threshold trigger otomatis
    trigger_rain_mm = Column(Float, default=50.0)   # hujan > 50mm/hari = banjir
    trigger_dry_days = Column(Float, default=7.0)   # 0mm selama 7 hari = kekeringan
    trigger_temp_max = Column(Float, default=38.0)  # suhu > 38°C = ekstrem

    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer")
    farm = relationship("Farm")
    claims = relationship("InsuranceClaim", back_populates="policy")


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("insurance_policies.id"), nullable=False)
    farmer_id = Column(UUID(as_uuid=True), ForeignKey("farmers.id"), nullable=False)
    trigger_type = Column(String(50), nullable=False)  # banjir, kekeringan, suhu_ekstrem
    trigger_value = Column(Float, nullable=False)      # nilai yang memicu (misal: 75mm hujan)
    trigger_threshold = Column(Float, nullable=False)  # threshold yang diset (misal: 50mm)
    claim_amount = Column(Float, nullable=False)
    status = Column(String(20), default="approved")    # auto-approved karena parametrik
    weather_date = Column(DateTime, nullable=False)    # tanggal kejadian cuaca
    created_at = Column(DateTime, default=datetime.utcnow)

    policy = relationship("InsurancePolicy", back_populates="claims")
    farmer = relationship("Farmer")