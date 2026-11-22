"""
Plant disease diagnosis using the Gemini API (google-genai SDK).

Design notes:
- One multimodal call: the image is sent inline as bytes, no public URL needed.
- Structured output: the response is constrained to DiagnosisResult, so enum
  fields (severity, urgency) can only take valid values and no JSON regex
  cleanup or second "language fixer" model is required.
- Model fallback: free-tier quotas differ per model and per project, so the
  service tries each model in GEMINI_MODELS until one succeeds.
- Image upload to Supabase Storage is best-effort and never blocks diagnosis.
"""

import json
import logging
import uuid
from typing import List, Literal, Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini status codes that justify trying the next model.
# 404: model unavailable for this key, 429: quota exhausted, 500/503: transient.
RETRYABLE_STATUS = {404, 429, 500, 503}


class DiagnosisError(Exception):
    """Raised when no configured Gemini model could produce a diagnosis."""


class DiagnosisResult(BaseModel):
    is_plant: bool = Field(
        description="True jika foto memperlihatkan tanaman dengan cukup jelas untuk dianalisis."
    )
    disease_name: str = Field(
        description="Nama penyakit/hama/gangguan dalam Bahasa Indonesia yang umum dipakai petani. "
        "Tulis 'Sehat' jika tidak ada masalah, atau 'Foto tidak valid' jika is_plant false."
    )
    confidence_score: float = Field(
        description="Tingkat keyakinan diagnosis antara 0.0 dan 1.0. Gunakan nilai rendah jika gejala ambigu."
    )
    severity: Literal["sehat", "ringan", "sedang", "parah"]
    cause_explanation: str = Field(
        description="1-2 kalimat sederhana yang menjelaskan MENGAPA masalah ini terjadi."
    )
    warning_signs: str = Field(
        description="Gejala yang benar-benar terlihat di foto, dideskripsikan secara konkret."
    )
    action_steps: List[str] = Field(
        description="Tepat 3 langkah: (1) tindakan hari ini, (2) tindakan 3-7 hari ke depan, "
        "(3) pencegahan jangka panjang."
    )
    urgency: Literal["segera (dalam 24 jam)", "minggu ini", "tidak mendesak"]
    estimated_yield_impact: str = Field(
        description="Perkiraan dampak ke hasil panen jika tidak ditangani, dalam bahasa sederhana."
    )
    preventive_measures: str = Field(
        description="Langkah pencegahan untuk musim tanam berikutnya."
    )


PROMPT_TEMPLATE = """Kamu adalah penyuluh pertanian berpengalaman di Indonesia yang berbicara \
langsung kepada petani kecil.

Konteks lahan: tanaman yang terdaftar adalah "{crop_type}". Jika foto jelas menunjukkan \
tanaman lain, analisis tanaman yang terlihat di foto.

Tugas: analisis foto ini dan diagnosis kondisi tanamannya.

Aturan:
- Gunakan Bahasa Indonesia yang baku, sederhana, dan mudah dipahami petani lulusan SD.
- Jangan mengarang nama penyakit. Jika gejalanya bisa berasal dari beberapa penyebab \
(misalnya virus vs kekurangan unsur hara), sebutkan penyebab yang paling mungkin, sebut \
kemungkinan lainnya di cause_explanation, dan turunkan confidence_score.
- Rekomendasi bahan (pestisida/pupuk) harus yang umum tersedia di toko pertanian Indonesia, \
dengan menyebut jenis/bahan aktifnya (misalnya "fungisida berbahan aktif mankozeb"), bukan merek.
- Jika foto bukan tanaman atau terlalu buram, set is_plant=false, disease_name="Foto tidak valid", \
confidence_score=0, severity="sehat", urgency="tidak mendesak", dan jelaskan di warning_signs \
foto seperti apa yang dibutuhkan.
{weather_section}"""

WEATHER_SECTION_TEMPLATE = """
Data cuaca di lokasi lahan ini (Open-Meteo), {weather_context}
Cara memakai data cuaca:
- Gejala yang terlihat di foto tetap dasar UTAMA diagnosis. Jangan menyimpulkan penyakit dari cuaca saja.
- Pakai cuaca hanya sebagai bukti pendukung untuk memilih di antara penyebab yang gejalanya mirip \
(misalnya kelembapan tinggi berhari-hari mendukung penyakit jamur, cuaca kering dan panas mendukung \
serangan tungau/thrips).
- Jika cuaca relevan dengan penyebabnya, sebutkan angkanya secara konkret di cause_explanation \
(contoh: "kelembapan di atas 85% selama 5 hari terakhir"), dan pertimbangkan cuaca saat menyusun action_steps.
- Jika cuaca tidak relevan, abaikan dan jangan menyebutnya.
"""


def _client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise DiagnosisError("GEMINI_API_KEY belum diisi di file .env")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _model_candidates() -> List[str]:
    models = [m.strip() for m in settings.GEMINI_MODELS.split(",") if m.strip()]
    if not models:
        raise DiagnosisError("GEMINI_MODELS kosong di file .env")
    return models


def build_prompt(crop_type: str, weather_context: Optional[str] = None) -> str:
    weather_section = (
        WEATHER_SECTION_TEMPLATE.format(weather_context=weather_context)
        if weather_context
        else ""
    )
    return PROMPT_TEMPLATE.format(
        crop_type=crop_type or "tidak diketahui", weather_section=weather_section
    )


async def _call_gemini(
    client: genai.Client, model: str, image_bytes: bytes, mime_type: str, prompt: str
) -> DiagnosisResult:
    response = await client.aio.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DiagnosisResult,
            temperature=0.2,
        ),
    )

    parsed = response.parsed
    if isinstance(parsed, DiagnosisResult):
        return parsed
    if response.text:
        return DiagnosisResult.model_validate_json(response.text)
    raise DiagnosisError(f"Model {model} mengembalikan respons kosong (kemungkinan diblokir safety filter)")


async def upload_to_storage(image_bytes: bytes, filename: str, mime_type: str) -> str:
    """Best-effort upload to Supabase Storage. Returns '' when not configured or on failure."""
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY):
        return ""
    try:
        from supabase import create_client

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        path = f"{uuid.uuid4()}_{filename}"
        supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
            path=path, file=image_bytes, file_options={"content-type": mime_type}
        )
        return supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(path)
    except Exception as exc:  # storage must never block a diagnosis
        logger.warning("Supabase upload failed, continuing without image_url: %s", exc)
        return ""


async def diagnose_plant(
    image_bytes: bytes,
    filename: str,
    mime_type: str,
    crop_type: str,
    weather_context: Optional[str] = None,
) -> dict:
    """
    Diagnose a plant photo. Returns a dict ready to be stored in the Diagnosis model.
    Raises DiagnosisError if every configured model fails.
    """
    client = _client()
    prompt = build_prompt(crop_type, weather_context)
    failures: List[str] = []
    result: Optional[DiagnosisResult] = None
    used_model = ""

    for model in _model_candidates():
        try:
            result = await _call_gemini(client, model, image_bytes, mime_type, prompt)
            used_model = model
            break
        except genai_errors.APIError as exc:
            failures.append(f"{model}: {exc.code} {exc.message}")
            logger.warning("Gemini model %s failed (%s), trying next", model, exc.code)
            if exc.code not in RETRYABLE_STATUS:
                break  # e.g. 400 bad request / 403 invalid key: other models won't help
        except (DiagnosisError, ValidationError, ValueError) as exc:
            failures.append(f"{model}: {exc}")
            logger.warning("Gemini model %s returned unusable output: %s", model, exc)
        except Exception as exc:  # network/timeout: other models won't help
            failures.append(f"{model}: {type(exc).__name__}: {exc}")
            logger.exception("Gemini request to %s failed", model)
            break

    if result is None:
        raise DiagnosisError("Semua model Gemini gagal. " + " | ".join(failures))

    logger.info("Diagnosis produced by %s", used_model)
    image_url = await upload_to_storage(image_bytes, filename, mime_type)

    return {
        "image_url": image_url,
        "disease_name": result.disease_name[:100],
        "confidence_score": max(0.0, min(1.0, result.confidence_score)),
        "severity": result.severity,
        "cause_explanation": result.cause_explanation,
        "warning_signs": result.warning_signs,
        "action_steps": json.dumps(result.action_steps, ensure_ascii=False),
        "urgency": result.urgency,
        "estimated_yield_impact": result.estimated_yield_impact,
        "preventive_measures": result.preventive_measures,
        "model": used_model,
        "weather_context": weather_context,
    }


def delete_stored_images(image_urls: List[str]) -> int:
    """
    Best-effort removal of diagnosis photos from Supabase Storage.
    Returns how many paths were sent for deletion; failures are logged, not raised.
    """
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY):
        return 0
    marker = f"/object/public/{settings.SUPABASE_BUCKET}/"
    paths = [url.split(marker, 1)[1].split("?", 1)[0] for url in image_urls if url and marker in url]
    if not paths:
        return 0
    try:
        from supabase import create_client

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        supabase.storage.from_(settings.SUPABASE_BUCKET).remove(paths)
        return len(paths)
    except Exception as exc:
        logger.warning("Failed to delete %d stored images: %s", len(paths), exc)
        return 0
