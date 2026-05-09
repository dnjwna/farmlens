from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api.auth import router as auth_router, farm_router
import app.models.farmer

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FarmLens API",
    description="Platform AI untuk petani kecil Indonesia",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(farm_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "FarmLens API berjalan", "docs": "/docs"}