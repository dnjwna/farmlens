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
    GEMINI_MODELS: str = "gemini-2.5-flash,gemini-flash-latest,gemini-2.5-flash-lite"

    # Supabase Storage for diagnosis photos (optional; diagnosis works without it)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "diagnoses"


settings = Settings()
