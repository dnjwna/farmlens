from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Gemini API (https://aistudio.google.com/apikey)
    GEMINI_API_KEY: str = ""
    # Comma-separated, tried in order. Free-tier quota differs per model and per
    # project, so the service falls back to the next model on 404/429/5xx.
    # Optional separate key for scripts/evaluate_diagnosis.py, so evaluation runs do not
    # consume the free-tier quota that the app needs for real diagnoses.
    EVAL_GEMINI_API_KEY: str = ""
    GEMINI_MODELS: str = "gemini-2.5-flash,gemini-flash-latest,gemini-2.5-flash-lite"

    # Supabase Storage for diagnosis photos (optional; diagnosis works without it)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "diagnoses"

    # Daily parametric-insurance check
    # In-process scheduler (fine for a single server). Disable it if an external
    # cron calls the admin endpoint instead, to keep one source of truth.
    INSURANCE_SCHEDULER_ENABLED: bool = True
    INSURANCE_CHECK_HOUR: int = 6  # local time, Asia/Jakarta
    # Protects /api/v1/admin/*. Empty = admin endpoints disabled.
    ADMIN_API_KEY: str = ""

    # Password-reset OTP delivery: "console" (dev: code printed in the server log) or "openwa"
    OTP_PROVIDER: str = "console"
    OPENWA_BASE_URL: str = "http://localhost:2785/api"
    OPENWA_API_KEY: str = ""
    OPENWA_SESSION_ID: str = ""


settings = Settings()
