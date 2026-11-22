"""
Parametric insurance: policy creation and the daily claim check.

The claim logic is split in two:
- evaluate_policy(): a pure function deciding which claims a policy earns for
  one day of weather. No database, no network, so every rule is unit-testable.
- run_daily_insurance_check(): loads policies, fetches weather, calls
  evaluate_policy() and persists the result.

Rules (all evaluated on the last COMPLETED day, Asia/Jakarta time):
- Payouts are triggered by weather that already happened, never by forecasts.
- Waiting period: only days strictly after the purchase day count, so weather
  already known when buying cannot trigger a claim.
- One claim per (policy, trigger type, day). Drought pays once per dry spell.
- Total payouts never exceed the policy's coverage_amount.
"""

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.farmer import Farm, InsuranceClaim, InsurancePolicy
from app.schemas.farmer import PolicyCreate
from app.services.weather_service import get_daily_observations

logger = logging.getLogger(__name__)

JAKARTA = ZoneInfo("Asia/Jakarta")

# Share of coverage_amount paid per trigger.
PAYOUT_SHARE = {"banjir": 0.5, "kekeringan": 0.4, "suhu_ekstrem": 0.3}

# A day with less rain than this (mm) counts as dry. Light drizzle does not
# relieve drought stress, so requiring exactly 0 mm would understate dry spells.
DRY_DAY_MAX_MM = 1.0

MIN_LOOKBACK_DAYS = 7


# ---------------------------------------------------------------------------
# Policy creation
# ---------------------------------------------------------------------------

def create_policy(db: Session, farmer_id: str, data: PolicyCreate) -> InsurancePolicy:
    farm = db.query(Farm).filter(
        Farm.id == data.farm_id, Farm.farmer_id == farmer_id, Farm.deleted_at.is_(None)
    ).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Lahan tidak ditemukan")
    if farm.latitude is None or farm.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="Lahan ini belum punya lokasi. Cuaca tidak bisa dipantau, jadi polis tidak bisa dibuat.",
        )

    existing = db.query(InsurancePolicy).filter(
        InsurancePolicy.farm_id == data.farm_id, InsurancePolicy.status == "active"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lahan ini sudah memiliki polis aktif")

    start_date = datetime.utcnow()
    policy = InsurancePolicy(
        farmer_id=farmer_id,
        farm_id=data.farm_id,
        premium_amount=data.premium_amount,
        coverage_amount=data.coverage_amount,
        start_date=start_date,
        end_date=start_date + timedelta(days=30 * data.duration_months),
        trigger_rain_mm=data.trigger_rain_mm,
        trigger_dry_days=data.trigger_dry_days,
        trigger_temp_max=data.trigger_temp_max,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


# ---------------------------------------------------------------------------
# Pure evaluation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DailyObservation:
    day: date
    rain_mm: Optional[float]
    temp_max: Optional[float]


@dataclass(frozen=True)
class ClaimDecision:
    trigger_type: str
    trigger_value: float
    trigger_threshold: float
    claim_amount: float
    weather_date: date


def utc_naive_to_jakarta_date(value: datetime) -> date:
    """DB timestamps are naive UTC (datetime.utcnow)."""
    return value.replace(tzinfo=ZoneInfo("UTC")).astimezone(JAKARTA).date()


def evaluate_policy(
    *,
    rain_threshold: float,
    dry_days_threshold: float,
    temp_threshold: float,
    coverage_amount: float,
    policy_start: date,
    policy_end: date,
    observations: list[DailyObservation],
    existing_claims: Iterable[tuple[str, date]],
    paid_so_far: float,
) -> list[ClaimDecision]:
    """
    Decide which claims a policy earns for the last day in `observations`.
    `observations` must be sorted oldest-first and end at the evaluated day.
    """
    if not observations:
        return []
    today = observations[-1]
    # Waiting period: only days strictly after the purchase day are covered.
    if not (policy_start < today.day <= policy_end):
        return []

    existing = set(existing_claims)
    remaining = coverage_amount - paid_so_far
    decisions: list[ClaimDecision] = []

    def add(trigger: str, value: float, threshold: float) -> None:
        nonlocal remaining
        if remaining <= 0:
            return
        amount = round(min(PAYOUT_SHARE[trigger] * coverage_amount, remaining), 2)
        decisions.append(ClaimDecision(trigger, value, threshold, amount, today.day))
        remaining -= amount

    # 1) Extreme rain on the evaluated day
    if today.rain_mm is not None and today.rain_mm > rain_threshold and ("banjir", today.day) not in existing:
        add("banjir", today.rain_mm, rain_threshold)

    # 2) Extreme heat on the evaluated day
    if today.temp_max is not None and today.temp_max > temp_threshold and ("suhu_ekstrem", today.day) not in existing:
        add("suhu_ekstrem", today.temp_max, temp_threshold)

    # 3) Drought: consecutive dry days ending on the evaluated day, counted only
    #    inside the coverage window. Missing data breaks the streak (conservative).
    streak = 0
    for obs in reversed(observations):
        if obs.day <= policy_start or obs.rain_mm is None or obs.rain_mm >= DRY_DAY_MAX_MM:
            break
        streak += 1
    if streak >= dry_days_threshold:
        streak_start = today.day - timedelta(days=streak - 1)
        already_paid_this_spell = any(t == "kekeringan" and d >= streak_start for t, d in existing)
        if not already_paid_this_spell:
            add("kekeringan", float(streak), dry_days_threshold)

    return decisions


# ---------------------------------------------------------------------------
# Daily job
# ---------------------------------------------------------------------------

async def run_daily_insurance_check(db: Session, today: Optional[date] = None) -> dict:
    """
    Evaluate every active policy for the last completed day and store new claims.
    Safe to run more than once a day: existing claims are never duplicated.
    """
    today = today or datetime.now(JAKARTA).date()
    evaluated_day = today - timedelta(days=1)

    # Expire finished policies first.
    expired = 0
    for policy in db.query(InsurancePolicy).filter(InsurancePolicy.status == "active").all():
        if utc_naive_to_jakarta_date(policy.end_date) < evaluated_day:
            policy.status = "expired"
            expired += 1
    db.commit()

    policies = db.query(InsurancePolicy).filter(InsurancePolicy.status == "active").all()
    summary = {
        "evaluated_day": evaluated_day.isoformat(),
        "policies_checked": 0,
        "policies_expired": expired,
        "claims_created": 0,
        "errors": [],
    }

    weather_cache: dict[tuple[float, float, int], list[DailyObservation]] = {}

    for policy in policies:
        farm = db.query(Farm).filter(Farm.id == policy.farm_id).first()
        if not farm or farm.latitude is None or farm.longitude is None:
            summary["errors"].append(f"{policy.id}: lahan tanpa lokasi")
            continue

        lookback = max(MIN_LOOKBACK_DAYS, math.ceil(policy.trigger_dry_days) + 1)
        key = (round(farm.latitude, 3), round(farm.longitude, 3), lookback)
        try:
            if key not in weather_cache:
                rows = await get_daily_observations(farm.latitude, farm.longitude, lookback)
                weather_cache[key] = [
                    DailyObservation(date.fromisoformat(r["date"]), r["rain_mm"], r["temp_max"]) for r in rows
                ]
            observations = [o for o in weather_cache[key] if o.day <= evaluated_day]
            if not observations or observations[-1].day != evaluated_day:
                summary["errors"].append(f"{policy.id}: data cuaca {evaluated_day} belum tersedia")
                continue

            claims = db.query(InsuranceClaim).filter(InsuranceClaim.policy_id == policy.id).all()
            decisions = evaluate_policy(
                rain_threshold=policy.trigger_rain_mm,
                dry_days_threshold=policy.trigger_dry_days,
                temp_threshold=policy.trigger_temp_max,
                coverage_amount=policy.coverage_amount,
                policy_start=utc_naive_to_jakarta_date(policy.start_date),
                policy_end=utc_naive_to_jakarta_date(policy.end_date),
                observations=observations,
                existing_claims=[(c.trigger_type, c.weather_date.date()) for c in claims],
                paid_so_far=sum(c.claim_amount for c in claims if c.status == "approved"),
            )
            summary["policies_checked"] += 1

            for d in decisions:
                db.add(
                    InsuranceClaim(
                        policy_id=policy.id,
                        farmer_id=policy.farmer_id,
                        trigger_type=d.trigger_type,
                        trigger_value=d.trigger_value,
                        trigger_threshold=d.trigger_threshold,
                        claim_amount=d.claim_amount,
                        weather_date=datetime.combine(d.weather_date, datetime.min.time()),
                    )
                )
            db.commit()  # per policy, so one failure does not roll back the others
            summary["claims_created"] += len(decisions)
        except IntegrityError:
            db.rollback()  # another run already stored this claim (unique index)
            summary["errors"].append(f"{policy.id}: klaim sudah tercatat oleh proses lain")
        except Exception as exc:
            db.rollback()
            logger.exception("Insurance check failed for policy %s", policy.id)
            summary["errors"].append(f"{policy.id}: {type(exc).__name__}")

    logger.info("Daily insurance check: %s", summary)
    return summary
