import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models.farmer  # noqa: F401  (registers models before create_all)
from app.api.admin import router as admin_router
from app.api.auth import farm_router, router as auth_router
from app.api.diagnosis import router as diagnosis_router
from app.api.insurance import router as insurance_router
from app.api.weather import router as weather_router
from app.core.config import settings
from sqlalchemy import text

from app.core.database import Base, SessionLocal, engine
from app.core.phone import normalize_existing_phone_numbers
from app.core.scheduler import insurance_scheduler_loop

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

def init_db() -> None:
    """Runs at startup (not import), so tests can import the app without a database."""
    Base.metadata.create_all(bind=engine)

    # create_all() only creates missing tables; it never adds columns to existing ones.
    # Lightweight, idempotent schema upgrades for columns added after the first deploy.
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE farms ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE farmers ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0"))

    # One-time (idempotent) normalization of phone numbers stored before +62 became canonical.
    with SessionLocal() as db:
        normalize_existing_phone_numbers(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    task = None
    if settings.INSURANCE_SCHEDULER_ENABLED:
        task = asyncio.create_task(insurance_scheduler_loop())
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="FarmLens API",
    description="Platform AI untuk petani kecil Indonesia",
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth_router, farm_router, diagnosis_router, weather_router, insurance_router, admin_router):
    app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "FarmLens API berjalan", "docs": "/docs"}
