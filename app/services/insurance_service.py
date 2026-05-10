from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta
from app.models.farmer import InsurancePolicy, InsuranceClaim, Farm
from app.schemas.farmer import PolicyCreate
from app.services.weather_service import get_weather
import asyncio

def create_policy(db: Session, farmer_id: str, data: PolicyCreate) -> InsurancePolicy:
    # Validasi farm milik petani
    farm = db.query(Farm).filter(
        Farm.id == data.farm_id,
        Farm.farmer_id == farmer_id
    ).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Lahan tidak ditemukan")

    # Cek tidak ada polis aktif untuk farm yang sama
    existing = db.query(InsurancePolicy).filter(
        InsurancePolicy.farm_id == data.farm_id,
        InsurancePolicy.status == "active"
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Lahan ini sudah memiliki polis aktif"
        )

    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=30 * data.duration_months)

    policy = InsurancePolicy(
        farmer_id=farmer_id,
        farm_id=data.farm_id,
        premium_amount=data.premium_amount,
        coverage_amount=data.coverage_amount,
        start_date=start_date,
        end_date=end_date,
        trigger_rain_mm=data.trigger_rain_mm,
        trigger_dry_days=data.trigger_dry_days,
        trigger_temp_max=data.trigger_temp_max,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


async def check_and_trigger_claims(db: Session) -> list:
    """
    Cek semua polis aktif dan trigger klaim otomatis jika ada anomali cuaca.
    Fungsi ini dipanggil scheduler setiap hari.
    """
    claims_created = []

    active_policies = db.query(InsurancePolicy).filter(
        InsurancePolicy.status == "active",
        InsurancePolicy.end_date > datetime.utcnow()
    ).all()

    for policy in active_policies:
        farm = db.query(Farm).filter(Farm.id == policy.farm_id).first()
        if not farm or not farm.latitude or not farm.longitude:
            continue

        try:
            weather = await get_weather(farm.latitude, farm.longitude)
            today = weather["forecast_7_days"][0]

            # Cek apakah klaim untuk hari ini sudah ada
            today_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            existing_claim = db.query(InsuranceClaim).filter(
                InsuranceClaim.policy_id == policy.id,
                InsuranceClaim.weather_date >= today_date
            ).first()
            if existing_claim:
                continue

            # --- TRIGGER 1: Banjir (hujan ekstrem) ---
            if today["rain_mm"] > policy.trigger_rain_mm:
                claim = InsuranceClaim(
                    policy_id=policy.id,
                    farmer_id=policy.farmer_id,
                    trigger_type="banjir",
                    trigger_value=today["rain_mm"],
                    trigger_threshold=policy.trigger_rain_mm,
                    claim_amount=policy.coverage_amount * 0.5,  # 50% coverage
                    weather_date=datetime.utcnow(),
                )
                db.add(claim)
                claims_created.append(claim)

            # --- TRIGGER 2: Suhu ekstrem ---
            elif today["temp_max"] > policy.trigger_temp_max:
                claim = InsuranceClaim(
                    policy_id=policy.id,
                    farmer_id=policy.farmer_id,
                    trigger_type="suhu_ekstrem",
                    trigger_value=today["temp_max"],
                    trigger_threshold=policy.trigger_temp_max,
                    claim_amount=policy.coverage_amount * 0.3,  # 30% coverage
                    weather_date=datetime.utcnow(),
                )
                db.add(claim)
                claims_created.append(claim)

            # --- TRIGGER 3: Kekeringan (7 hari tanpa hujan) ---
            else:
                dry_days = sum(
                    1 for day in weather["forecast_7_days"]
                    if day["rain_mm"] == 0
                )
                if dry_days >= policy.trigger_dry_days:
                    claim = InsuranceClaim(
                        policy_id=policy.id,
                        farmer_id=policy.farmer_id,
                        trigger_type="kekeringan",
                        trigger_value=dry_days,
                        trigger_threshold=policy.trigger_dry_days,
                        claim_amount=policy.coverage_amount * 0.4,  # 40% coverage
                        weather_date=datetime.utcnow(),
                    )
                    db.add(claim)
                    claims_created.append(claim)

        except Exception as e:
            print(f"Error checking policy {policy.id}: {e}")
            continue

    db.commit()
    return claims_created