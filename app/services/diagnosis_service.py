import httpx
import json
import re
import uuid
from supabase import create_client
from app.core.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

PROMPT = """
You are an Indonesian agricultural extension worker analyzing a plant photo.
Analyze this plant image and respond ONLY in this exact JSON format, no other text:
{
  "disease_name": "disease name in Indonesian, or 'Sehat' if healthy",
  "confidence_score": number between 0.0 and 1.0,
  "severity": "ringan or sedang or parah or sehat",
  "cause_explanation": "1-2 sentences WHY this disease occurs, simple language",
  "warning_signs": "what visible symptoms are seen in the photo, concrete description",
  "action_steps": [
    "First action to take today",
    "Second action within 3-7 days",
    "Third preventive action"
  ],
  "urgency": "segera (dalam 24 jam) or minggu ini or tidak mendesak",
  "estimated_yield_impact": "estimated impact on harvest if untreated",
  "preventive_measures": "prevention steps for next growing season"
}
If photo is not a plant or unclear, set disease_name to 'Foto tidak valid' and confidence_score to 0.0.
"""

FIX_LANGUAGE_PROMPT = """Kamu adalah editor Bahasa Indonesia profesional dan ahli pertanian.

Perbaiki teks JSON berikut dengan aturan:
1. Semua nilai string harus dalam Bahasa Indonesia yang benar dan natural
2. Jangan ubah struktur JSON, key, atau nilai numerik
3. Untuk field "urgency", HANYA boleh berisi salah satu dari: "segera (dalam 24 jam)", "minggu ini", "tidak mendesak"
4. Untuk field "severity", HANYA boleh berisi salah satu dari: "ringan", "sedang", "parah", "sehat"
5. Perbaiki kata-kata yang aneh, salah terjemah, atau tidak natural
6. Kembalikan HANYA JSON yang sudah diperbaiki, tanpa teks lain

JSON yang perlu diperbaiki:
{json_text}"""


async def fix_language(result: dict) -> dict:
    try:
        json_text = json.dumps(result, ensure_ascii=False, indent=2)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen/qwen3-next-80b-a3b-instruct:free",
                    "thinking": {"type": "disabled"},
                    "messages": [
                        {
                            "role": "user",
                            "content": FIX_LANGUAGE_PROMPT.format(json_text=json_text)
                        }
                    ]
                }
            )

        response.raise_for_status()
        data = response.json()
        text = data['choices'][0]['message']['content'].strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group()

        fixed = json.loads(text)
        fixed['image_url'] = result.get('image_url', '')
        return fixed

    except Exception as e:
        print(f"Language fix failed (using original): {e}")
        return result


async def upload_to_storage(image_bytes: bytes, filename: str) -> str:
    unique_filename = f"{uuid.uuid4()}_{filename}"
    supabase.storage.from_("diagnoses").upload(
        path=unique_filename,
        file=image_bytes,
        file_options={"content-type": "image/jpeg"}
    )
    return supabase.storage.from_("diagnoses").get_public_url(unique_filename)


async def diagnose_plant(image_bytes: bytes, filename: str) -> dict:
    try:
        image_url = await upload_to_storage(image_bytes, filename)

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
                                {"type": "text", "text": PROMPT},
                                {"type": "image_url", "image_url": {"url": image_url}}
                            ]
                        }
                    ]
                }
            )

        response.raise_for_status()
        data = response.json()
        text = data['choices'][0]['message']['content'].strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group()

        result = json.loads(text)
        result['image_url'] = image_url

        if isinstance(result.get('action_steps'), list):
            result['action_steps'] = json.dumps(result['action_steps'], ensure_ascii=False)

        result = await fix_language(result)

        if isinstance(result.get('action_steps'), list):
            result['action_steps'] = json.dumps(result['action_steps'], ensure_ascii=False)

        return result

    except json.JSONDecodeError:
        return {
            "disease_name": "Gagal menganalisis",
            "confidence_score": 0.0,
            "severity": "tidak diketahui",
            "cause_explanation": "Foto tidak dapat dianalisis oleh sistem.",
            "warning_signs": "-",
            "action_steps": "[]",
            "urgency": "tidak mendesak",
            "estimated_yield_impact": "-",
            "preventive_measures": "Coba upload foto yang lebih jelas dan terang.",
            "image_url": ""
        }
    except Exception as e:
        raise Exception(f"Diagnosis error: {str(e)}")