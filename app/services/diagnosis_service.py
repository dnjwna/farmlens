import httpx
import base64
import json
import re
from app.core.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PROMPT = """
Kamu adalah ahli agronomis Indonesia yang berpengalaman mendiagnosis penyakit tanaman.

Analisis foto tanaman ini dan berikan respons HANYA dalam format JSON berikut, tanpa teks lain:
{
  "disease_name": "nama penyakit dalam Bahasa Indonesia, atau 'Sehat' jika tidak ada penyakit",
  "confidence_score": angka antara 0.0 sampai 1.0,
  "severity": "ringan / sedang / parah / sehat",
  "recommendation": "rekomendasi penanganan detail dalam Bahasa Indonesia, minimal 3 kalimat",
  "preventive_measures": "langkah pencegahan untuk masa depan dalam Bahasa Indonesia"
}

Jika foto bukan tanaman atau tidak jelas, isi disease_name dengan 'Foto tidak valid' dan confidence_score dengan 0.0.
"""

async def diagnose_plant(image_bytes: bytes) -> dict:
    try:
        # Encode gambar ke base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "nvidia/nemotron-nano-12b-v2-vl:free",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": PROMPT
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ]
                }
            )

        response.raise_for_status()
        data = response.json()
        text = data['choices'][0]['message']['content'].strip()

        # Bersihkan markdown code block kalau ada
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        result = json.loads(text)
        return result

    except json.JSONDecodeError:
        return {
            "disease_name": "Gagal menganalisis",
            "confidence_score": 0.0,
            "severity": "tidak diketahui",
            "recommendation": "Foto tidak dapat dianalisis. Coba upload foto yang lebih jelas.",
            "preventive_measures": "-"
        }
    except Exception as e:
        raise Exception(f"OpenRouter API error: {str(e)}")