"""
Check which Gemini models your API key can actually use for diagnosis.

Usage (from the project root, venv active):
    python scripts/check_gemini.py

It lists vision-capable models, then sends a tiny text request to each model in
GEMINI_MODELS and reports OK / quota / not-found, so you can reorder the list.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai  # noqa: E402
from google.genai import errors  # noqa: E402

from app.core.config import settings  # noqa: E402


def main() -> int:
    if not settings.GEMINI_API_KEY:
        print("GEMINI_API_KEY kosong di .env")
        return 1

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    print("Model 'flash' yang tersedia untuk key ini:")
    for m in client.models.list():
        name = m.name.removeprefix("models/")
        if "flash" in name and "generateContent" in (m.supported_actions or []):
            print("  -", name)

    print("\nTes GEMINI_MODELS (urutan fallback):")
    ok = False
    for model in [x.strip() for x in settings.GEMINI_MODELS.split(",") if x.strip()]:
        try:
            r = client.models.generate_content(model=model, contents="Jawab satu kata: halo")
            print(f"  OK    {model}: {r.text.strip()[:40]!r}")
            ok = True
        except errors.APIError as e:
            label = {429: "QUOTA", 404: "N/A"}.get(e.code, str(e.code))
            print(f"  {label:<5} {model}: {e.message[:120]}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
