"""
Run the daily parametric-insurance check once, outside the web server.

Usage (from the project root, venv active):
    python scripts/run_insurance_check.py              # evaluates yesterday
    python scripts/run_insurance_check.py 2026-11-21   # evaluates the day BEFORE this date
"""
import asyncio
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.services.insurance_service import run_daily_insurance_check  # noqa: E402


async def main() -> None:
    today = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        summary = await run_daily_insurance_check(db, today=today)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
