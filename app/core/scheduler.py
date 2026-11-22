"""
Minimal in-process daily scheduler for the parametric-insurance check.

Runs once shortly after startup (to catch up if the server was down at the
scheduled hour) and then every day at INSURANCE_CHECK_HOUR Asia/Jakarta.
The check is idempotent, so the catch-up run never creates duplicate claims.

Limitation: with several server instances/workers each one runs the job. The
app-level duplicate check plus the optional unique index (see
scripts/sql/insurance_claims_unique.sql) keep that safe, but for multi-instance
deployments prefer INSURANCE_SCHEDULER_ENABLED=false + an external cron calling
POST /api/v1/admin/insurance/run-daily-check.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.insurance_service import run_daily_insurance_check

logger = logging.getLogger(__name__)
JAKARTA = ZoneInfo("Asia/Jakarta")
STARTUP_DELAY_SECONDS = 30


def seconds_until_next_run(now: datetime, hour: int) -> float:
    next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


async def _run_once() -> None:
    db = SessionLocal()
    try:
        summary = await run_daily_insurance_check(db)
        logger.info("Insurance check done: %s", summary)
    except Exception:
        logger.exception("Insurance check crashed")
    finally:
        db.close()


async def insurance_scheduler_loop() -> None:
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    await _run_once()
    while True:
        wait = seconds_until_next_run(datetime.now(JAKARTA), settings.INSURANCE_CHECK_HOUR)
        logger.info("Next insurance check in %.0f minutes", wait / 60)
        await asyncio.sleep(wait)
        await _run_once()
