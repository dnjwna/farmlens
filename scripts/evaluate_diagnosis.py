"""
Offline evaluation of the diagnosis model, with an optional weather ablation.

Usage (from the project root, venv active):
    # 1. inference (resumable: rerun the same command to continue after an interruption)
    python scripts/evaluate_diagnosis.py run \
        --manifest data/eval/manifest.csv --labels data/eval/labels.json --out eval_results/run1

    # 2. re-score after editing aliases in labels.json (no model calls)
    python scripts/evaluate_diagnosis.py score --out eval_results/run1 --labels data/eval/labels.json

Conditions:
    no_weather        prompt without weather (every sample)
    weather           real weather for the 7 days before the photo (samples with lat, lon, taken_at)
    weather_shuffled  weather of a different sample (placebo control, same samples as `weather`)

The model is fixed with --model and never falls back to another model, so the
comparison is not confounded by which model happened to answer.
"""
import argparse
import asyncio
import csv
import hashlib
import io
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402
from google import genai  # noqa: E402
from google.genai import errors as genai_errors  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.evaluation.labels import LabelSet, load_labels, normalize_text  # noqa: E402
from app.evaluation.metrics import derangement  # noqa: E402
from app.evaluation.scoring import compute_summary, load_records, write_outputs  # noqa: E402
from app.evaluation.weather_history import weather_context_for_date  # noqa: E402
from app.services import diagnosis_service as ds  # noqa: E402

ALL_CONDITIONS = ("no_weather", "weather", "weather_shuffled")
WEATHER_CONDITIONS = {"weather", "weather_shuffled"}
RETRYABLE = {429, 500, 503}
MAX_CONSECUTIVE_FAILURES = 10

# Mirrors frontend/src/lib/image.ts
SKIP_BELOW_BYTES = 300 * 1024
MAX_DIMENSION = 1024
JPEG_QUALITY = 80
PASSTHROUGH_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

@dataclass
class Sample:
    sample_id: str
    path: Path
    crop: str
    label: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    taken_at: Optional[date] = None

    @property
    def has_weather_inputs(self) -> bool:
        return self.lat is not None and self.lon is not None and self.taken_at is not None


def _parse_float(value: str, field: str, line: int, errors: list) -> Optional[float]:
    if not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        errors.append(f"baris {line}: {field} bukan angka: {value!r}")
        return None


def load_manifest(path: Path, labels: LabelSet) -> list[Sample]:
    """CSV columns: path,crop,label[,lat,lon,taken_at]. Paths are relative to the manifest."""
    base = path.parent
    samples, errors, seen = [], [], set()
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = {"path", "crop", "label"} - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{path}: kolom wajib tidak ada: {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            rel = (row.get("path") or "").strip()
            crop = (row.get("crop") or "").strip()
            label = (row.get("label") or "").strip()
            if not (rel and crop and label):
                errors.append(f"baris {line}: path, crop dan label wajib diisi")
                continue
            file_path = (base / rel).resolve()
            if not file_path.is_file():
                errors.append(f"baris {line}: file tidak ditemukan: {rel}")
            cls = labels.classes.get(label)
            if cls is None:
                errors.append(f"baris {line}: label {label!r} tidak ada di labels.json")
            elif normalize_text(cls.crop) != normalize_text(crop):
                errors.append(f"baris {line}: label {label!r} milik tanaman {cls.crop!r}, bukan {crop!r}")
            sample_id = Path(rel).as_posix()
            if sample_id in seen:
                errors.append(f"baris {line}: path duplikat: {rel}")
            seen.add(sample_id)

            taken = None
            raw_taken = (row.get("taken_at") or "").strip()
            if raw_taken:
                try:
                    taken = date.fromisoformat(raw_taken[:10])
                except ValueError:
                    errors.append(f"baris {line}: taken_at harus YYYY-MM-DD: {raw_taken!r}")
            lat = _parse_float(row.get("lat") or "", "lat", line, errors)
            lon = _parse_float(row.get("lon") or "", "lon", line, errors)
            samples.append(Sample(sample_id, file_path, crop, label, lat, lon, taken))

    if errors:
        shown = "\n  ".join(errors[:30])
        more = f"\n  ... dan {len(errors) - 30} lainnya" if len(errors) > 30 else ""
        raise SystemExit(f"Manifest tidak valid ({len(errors)} masalah):\n  {shown}{more}")
    if not samples:
        raise SystemExit("Manifest kosong")
    return samples


def stratified_subset(samples: list[Sample], limit: Optional[int], seed: int = 42) -> list[Sample]:
    """Deterministic, label-balanced subset for quick or budget-limited runs."""
    if not limit or limit >= len(samples):
        return samples
    rng = random.Random(seed)
    groups: dict[str, list[Sample]] = {}
    for s in sorted(samples, key=lambda s: s.sample_id):
        groups.setdefault(s.label, []).append(s)
    for g in groups.values():
        rng.shuffle(g)
    picked, queues = [], [list(g) for _, g in sorted(groups.items())]
    while len(picked) < limit and any(queues):
        for q in queues:
            if q and len(picked) < limit:
                picked.append(q.pop())
    return picked


def prepare_image(path: Path, compress: bool) -> tuple[bytes, str]:
    """Send what the app would send: small files as-is, larger ones resized to 1024 px JPEG."""
    raw = path.read_bytes()
    with Image.open(io.BytesIO(raw)) as img:
        fmt = img.format or ""
        if fmt in PASSTHROUGH_FORMATS and (not compress or len(raw) < SKIP_BELOW_BYTES):
            return raw, PASSTHROUGH_FORMATS[fmt]
        img = ImageOps.exif_transpose(img).convert("RGB")
        if compress:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        return buf.getvalue(), "image/jpeg"


# ---------------------------------------------------------------------------
# Run bookkeeping
# ---------------------------------------------------------------------------

def prompt_version() -> str:
    """Changes whenever the prompt or the output schema changes."""
    material = ds.PROMPT_TEMPLATE + ds.WEATHER_SECTION_TEMPLATE + json.dumps(
        ds.DiagnosisResult.model_json_schema(), sort_keys=True
    )
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def record_key(sample_id: str, condition: str, repeat: int, model: str, version: str) -> str:
    return hashlib.sha1(f"{sample_id}|{condition}|{repeat}|{model}|{version}".encode()).hexdigest()


def check_or_write_config(out: Path, config: dict) -> None:
    path = out / "config.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        for field in ("model", "prompt_version", "compress"):
            if old.get(field) != config[field]:
                raise SystemExit(
                    f"{out} dibuat dengan {field}={old.get(field)!r}, sekarang {config[field]!r}. "
                    "Pakai --out baru supaya hasil tidak tercampur."
                )
        config = {**old, **config, "created_at": old.get("created_at")}
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


class RateLimiter:
    """Spaces request starts at least 60/rpm seconds apart (free-tier friendly)."""

    def __init__(self, rpm: float):
        self.interval = 60.0 / rpm if rpm > 0 else 0.0
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = self._next - now
            self._next = max(now, self._next) + self.interval
        if delay > 0:
            await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

async def build_weather_contexts(samples: list[Sample], out: Path) -> dict[str, tuple[str, str]]:
    """sample_id -> (context, source), cached in weather_cache.json."""
    cache_path = out / "weather_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    eligible = [s for s in samples if s.has_weather_inputs]

    def cache_key(s: Sample) -> str:
        return f"{s.lat:.4f},{s.lon:.4f},{s.taken_at.isoformat()}"

    todo = sorted({cache_key(s): s for s in eligible if cache_key(s) not in cache}.items())
    if todo:
        print(f"Mengambil cuaca historis untuk {len(todo)} lokasi/tanggal...")
        sem = asyncio.Semaphore(4)
        async with httpx.AsyncClient(timeout=20.0) as client:
            async def fetch(key: str, s: Sample):
                async with sem:
                    ctx, source = await weather_context_for_date(client, s.lat, s.lon, s.taken_at)
                    cache[key] = {"context": ctx, "source": source}
            await asyncio.gather(*(fetch(k, s) for k, s in todo))
        cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

    contexts = {}
    for s in eligible:
        entry = cache.get(cache_key(s)) or {}
        if entry.get("context"):
            contexts[s.sample_id] = (entry["context"], entry["source"])
    missing = len(eligible) - len(contexts)
    if missing:
        print(f"Peringatan: cuaca tidak tersedia untuk {missing} sampel; sampel itu hanya dievaluasi tanpa cuaca.")
    return contexts


def shuffled_contexts(contexts: dict[str, tuple[str, str]]) -> dict[str, str]:
    ids = sorted(contexts)
    if len(ids) < 2:
        return {}
    donors = derangement(ids)
    shuffled = {sid: contexts[donor][0] for sid, donor in zip(ids, donors)}
    identical = sum(1 for sid in ids if shuffled[sid] == contexts[sid][0])
    if identical:
        print(
            f"Peringatan: {identical}/{len(ids)} konteks cuaca acak identik dengan aslinya "
            "(banyak foto dari lokasi/tanggal yang sama). Kontrol plasebo jadi lemah."
        )
    return shuffled


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

class QuotaExhausted(Exception):
    """Daily (or otherwise non-recoverable within this run) quota is used up."""


def describe_quota(exc: genai_errors.APIError) -> tuple[Optional[str], Optional[float], str]:
    """
    Reads Gemini's 429 details. Returns (scope, retry_after_seconds, description):
    scope is "day" for daily quotas (waiting seconds will not help), "minute" otherwise.
    """
    details = exc.details if isinstance(exc.details, dict) else {}
    items = (details.get("error") or {}).get("details") or []
    scope, retry_after, parts = None, None, []
    for item in items:
        kind = str(item.get("@type", ""))
        if kind.endswith("QuotaFailure"):
            for v in item.get("violations", []):
                quota_id = str(v.get("quotaId", ""))
                if "PerDay" in quota_id:
                    scope = "day"
                elif scope is None and quota_id:
                    scope = "minute"
                limit = v.get("quotaValue")
                parts.append(f"{quota_id or v.get('quotaMetric', 'quota')}" + (f" (batas {limit})" if limit else ""))
        elif kind.endswith("RetryInfo"):
            raw = str(item.get("retryDelay", "")).rstrip("s")
            try:
                retry_after = float(raw)
            except ValueError:
                pass
    return scope, retry_after, ", ".join(parts) or (exc.message or "kuota habis")


async def call_model(client, model: str, image: bytes, mime: str, prompt: str) -> ds.DiagnosisResult:
    for attempt in range(5):
        try:
            return await ds._call_gemini(client, model, image, mime, prompt)
        except genai_errors.APIError as exc:
            if exc.code == 429:
                scope, retry_after, desc = describe_quota(exc)
                if scope == "day":
                    raise QuotaExhausted(desc) from exc
            if exc.code in RETRYABLE and attempt < 4:
                retry_after = describe_quota(exc)[1] if exc.code == 429 else None
                wait = (retry_after or min(60, 4 * 2 ** attempt)) + random.uniform(0, 1)
                print(f"  {exc.code} dari Gemini, coba lagi dalam {wait:.0f} detik")
                await asyncio.sleep(wait)
                continue
            raise
        except (ds.DiagnosisError, ValidationError, ValueError):
            if attempt < 1:
                continue  # one retry for malformed or empty output
            raise
    raise RuntimeError("unreachable")


async def run(args) -> int:
    labels = load_labels(args.labels)
    samples = stratified_subset(load_manifest(Path(args.manifest), labels), args.limit)
    out = Path(args.out)
    model = args.model or ds._model_candidates()[0]
    version = prompt_version()
    config = {
        "model": model,
        "prompt_version": version,
        "compress": not args.no_compress,
        "manifest": str(args.manifest),
        "labels": str(args.labels),
        "conditions": args.conditions,
        "repeats": args.repeats,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    check_or_write_config(out, config)

    contexts: dict[str, tuple[str, str]] = {}
    placebo: dict[str, str] = {}
    if WEATHER_CONDITIONS & set(args.conditions):
        contexts = await build_weather_contexts(samples, out)
        if "weather_shuffled" in args.conditions:
            placebo = shuffled_contexts(contexts)
        if not contexts:
            print("Tidak ada sampel dengan lat, lon dan taken_at: kondisi cuaca dilewati.")

    raw_path = out / "raw.jsonl"
    done = {r["key"] for r in load_records(raw_path) if r.get("result") is not None}

    jobs = []
    for s in samples:
        for cond in args.conditions:
            if cond == "weather" and s.sample_id not in contexts:
                continue
            if cond == "weather_shuffled" and s.sample_id not in placebo:
                continue
            for rep in range(args.repeats):
                key = record_key(s.sample_id, cond, rep, model, version)
                if key not in done:
                    jobs.append((key, s, cond, rep))

    print(f"Model {model}, prompt {version}: {len(jobs)} panggilan baru, {len(done)} sudah ada di {raw_path}")
    if jobs and not args.yes:
        answer = input(f"Lanjut {len(jobs)} panggilan ke Gemini? [y/N] ").strip().lower()
        if answer not in ("y", "ya", "yes"):
            print("Dibatalkan.")
            return 1

    client = make_client()
    limiter = RateLimiter(args.rpm)
    sem = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()
    images: dict[str, tuple[bytes, str]] = {}
    state = {"done": 0, "consecutive_failures": 0, "aborted": False}

    async def worker(key: str, s: Sample, cond: str, rep: int) -> None:
        if state["aborted"]:
            return
        async with sem:
            if state["aborted"]:
                return
            if s.sample_id not in images:
                images[s.sample_id] = prepare_image(s.path, compress=not args.no_compress)
            image, mime = images[s.sample_id]
            weather = contexts[s.sample_id][0] if cond == "weather" else placebo.get(s.sample_id) if cond == "weather_shuffled" else None
            record = {
                "key": key, "sample_id": s.sample_id, "crop": s.crop, "label": s.label,
                "condition": cond, "repeat": rep, "model": model, "prompt_version": version,
                "weather_context": weather,
                "weather_source": contexts[s.sample_id][1] if cond == "weather" else ("shuffled" if weather else None),
                "image_bytes": len(image), "result": None, "error": None,
            }
            await limiter.wait()
            started = time.monotonic()
            try:
                result = await call_model(client, model, image, mime, ds.build_prompt(s.crop, weather))
                record["result"] = result.model_dump()
                state["consecutive_failures"] = 0
            except QuotaExhausted as exc:
                record["error"] = f"QuotaExhausted: {exc}"[:500]
                if not state["aborted"]:
                    state["aborted"] = True
                    state["quota"] = str(exc)
            except Exception as exc:  # recorded and retried on the next run
                record["error"] = f"{type(exc).__name__}: {exc}"[:500]
                state["consecutive_failures"] += 1
                if state["consecutive_failures"] >= MAX_CONSECUTIVE_FAILURES:
                    state["aborted"] = True
            record["latency_ms"] = round((time.monotonic() - started) * 1000)
            record["created_at"] = datetime.now(timezone.utc).isoformat()

            async with write_lock:
                with raw_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                state["done"] += 1
                res = record["result"]
                status = f"{res['disease_name']} ({res['confidence_score']:.2f})" if res else f"ERROR {record['error'][:80]}"
                print(f"[{state['done']}/{len(jobs)}] {s.sample_id} [{cond}] -> {status}")

    await asyncio.gather(*(worker(*job) for job in jobs))

    if state.get("quota"):
        print(f"\nKuota harian Gemini habis: {state['quota']}.\n"
              "Hasil yang sudah ada tersimpan. Jalankan perintah yang sama besok untuk melanjutkan, "
              "atau pakai EVAL_GEMINI_API_KEY dari project lain / project dengan billing.")
    elif state["aborted"]:
        print(f"\nBerhenti setelah {MAX_CONSECUTIVE_FAILURES} kegagalan berturut-turut (kuota habis atau API key salah?). "
              "Jalankan perintah yang sama lagi nanti untuk melanjutkan.")
    score(out, labels, args.threshold)
    return 2 if state["aborted"] else 0


def make_client():
    """Prefers EVAL_GEMINI_API_KEY so evaluation does not eat the app's quota."""
    if settings.EVAL_GEMINI_API_KEY:
        print("Memakai EVAL_GEMINI_API_KEY.")
        return genai.Client(api_key=settings.EVAL_GEMINI_API_KEY)
    print("Memakai GEMINI_API_KEY aplikasi (kuotanya ikut terpakai). Isi EVAL_GEMINI_API_KEY untuk memisahkannya.")
    return ds._client()


def score(out: Path, labels: LabelSet, threshold: float) -> None:
    config_path = out / "config.json"
    if not config_path.exists():
        raise SystemExit(f"{config_path} tidak ada. Jalankan `run` dulu.")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    records = load_records(out / "raw.jsonl")
    if not records:
        print("Belum ada hasil untuk dinilai.")
        return
    summary = compute_summary(records, labels, threshold)
    write_outputs(summary, config, out)
    for cond, s in summary["conditions"].items():
        lo, hi = s["accuracy_ci95"]
        print(f"{cond:17s} n={s['n']:4d}  akurasi {100 * s['accuracy']:.1f}% (95% CI {100 * lo:.1f}-{100 * hi:.1f})  "
              f"macro-F1 {s['macro_f1']:.3f}  tidak cocok alias {100 * s['unmatched_rate']:.1f}%")
    for c in summary["comparisons"]:
        lo, hi = c["diff_ci95"]
        print(f"{c['b']} vs {c['a']}: {100 * c['diff']:+.1f} pp (95% CI {100 * lo:+.1f} s/d {100 * hi:+.1f}), "
              f"p McNemar {c['mcnemar_p']:.3f}, n={c['n_paired']}")
    print(f"\nLaporan: {out / 'report.md'}  |  Detail: {out / 'predictions.csv'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="panggil model lalu nilai hasilnya")
    p_run.add_argument("--manifest", required=True)
    p_run.add_argument("--labels", required=True)
    p_run.add_argument("--out", required=True)
    p_run.add_argument("--model", help="default: model pertama di GEMINI_MODELS")
    p_run.add_argument("--conditions", nargs="+", choices=ALL_CONDITIONS, default=list(ALL_CONDITIONS))
    p_run.add_argument("--repeats", type=int, default=1, help="ulangi tiap panggilan untuk mengukur konsistensi")
    p_run.add_argument("--limit", type=int, help="ambil N sampel seimbang per label (untuk uji coba)")
    p_run.add_argument("--concurrency", type=int, default=2)
    p_run.add_argument("--rpm", type=float, default=10, help="maksimal panggilan per menit")
    p_run.add_argument("--threshold", type=float, default=0.7, help="batas confidence di aplikasi")
    p_run.add_argument("--no-compress", action="store_true", help="kirim gambar asli, bukan versi terkompres aplikasi")
    p_run.add_argument("-y", "--yes", action="store_true", help="jangan tanya konfirmasi")

    p_score = sub.add_parser("score", help="nilai ulang hasil yang sudah ada (tanpa memanggil model)")
    p_score.add_argument("--out", required=True)
    p_score.add_argument("--labels", required=True)
    p_score.add_argument("--threshold", type=float, default=0.7)

    args = parser.parse_args()
    if args.command == "run":
        if args.repeats < 1 or args.concurrency < 1:
            parser.error("--repeats dan --concurrency minimal 1")
        try:
            return asyncio.run(run(args))
        except KeyboardInterrupt:
            print("\nDihentikan. Hasil yang sudah selesai tersimpan; jalankan perintah yang sama untuk melanjutkan.")
            if (Path(args.out) / "raw.jsonl").exists():
                score(Path(args.out), load_labels(args.labels), args.threshold)
            return 130
    score(Path(args.out), load_labels(args.labels), args.threshold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
