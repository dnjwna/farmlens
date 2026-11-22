"""
Tests for the diagnosis evaluation: label matching, statistics, scoring and the runner
(with a fake model and fake weather; no network).

Run from the project root:
    python -m unittest tests.test_evaluation -v
"""
import asyncio
import importlib.util
import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from datetime import date
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/test")
os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from PIL import Image  # noqa: E402

from app.evaluation import metrics as m  # noqa: E402
from app.evaluation.labels import AMBIGUOUS, INVALID, UNMATCHED, LabelClass, LabelSet, match_prediction  # noqa: E402
from app.evaluation.scoring import compute_summary  # noqa: E402
from app.evaluation.weather_history import window_for  # noqa: E402
from app.services import diagnosis_service as ds  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("evaluate_diagnosis", ROOT / "scripts" / "evaluate_diagnosis.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

LABELS = LabelSet({
    "cabai_sehat": LabelClass("cabai_sehat", "cabai", True, ("sehat",)),
    "cabai_cercospora": LabelClass("cabai_cercospora", "cabai", False, ("cercospora", "bercak daun cercospora", "bercak daun")),
    "cabai_bercak_bakteri": LabelClass("cabai_bercak_bakteri", "cabai", False, ("bercak daun bakteri", "xanthomonas")),
    "cabai_antraknosa": LabelClass("cabai_antraknosa", "cabai", False, ("antraknosa",)),
    "padi_blas": LabelClass("padi_blas", "padi", False, ("blas", "blast")),
})


class MatchingTests(unittest.TestCase):
    def test_basic_and_case_punctuation(self):
        self.assertEqual(match_prediction(LABELS, "cabai", "Bercak Daun Cercospora (Cercospora capsici)")[0], "cabai_cercospora")
        self.assertEqual(match_prediction(LABELS, "Cabai", "ANTRAKNOSA!")[0], "cabai_antraknosa")

    def test_healthy(self):
        self.assertEqual(match_prediction(LABELS, "cabai", "Sehat")[0], "cabai_sehat")

    def test_restricted_to_crop(self):
        # "blast" belongs to padi only
        self.assertEqual(match_prediction(LABELS, "cabai", "Blast")[0], UNMATCHED)
        self.assertEqual(match_prediction(LABELS, "padi", "Penyakit Blast")[0], "padi_blas")

    def test_whole_word_only(self):
        self.assertEqual(match_prediction(LABELS, "padi", "Blastopora")[0], UNMATCHED)

    def test_nested_alias_and_hedging(self):
        # "bercak daun" (cercospora) is nested inside "bercak daun bakteri": bacterial wins
        self.assertEqual(match_prediction(LABELS, "cabai", "Bercak daun bakteri (Xanthomonas)")[0], "cabai_bercak_bakteri")
        self.assertEqual(match_prediction(LABELS, "cabai", "Bercak daun")[0], "cabai_cercospora")
        # Two diseases named: hedged answer is not credited
        self.assertEqual(match_prediction(LABELS, "cabai", "Antraknosa atau sehat")[0], AMBIGUOUS)
        self.assertEqual(match_prediction(LABELS, "cabai", "Antraknosa atau bercak daun bakteri")[0], AMBIGUOUS)
        # Same class repeated is fine
        self.assertEqual(match_prediction(LABELS, "cabai", "Cercospora (bercak daun cercospora)")[0], "cabai_cercospora")

    def test_invalid_photo(self):
        self.assertEqual(match_prediction(LABELS, "cabai", "Foto tidak valid", is_plant=False)[0], INVALID)


class MetricTests(unittest.TestCase):
    def test_wilson_reference_values(self):
        lo, hi = m.wilson_interval(8, 10)
        self.assertAlmostEqual(lo, 0.4902, places=3)
        self.assertAlmostEqual(hi, 0.9433, places=3)
        self.assertEqual(m.wilson_interval(0, 0), (0.0, 0.0))
        self.assertAlmostEqual(m.wilson_interval(10, 10)[1], 1.0)

    def test_mcnemar(self):
        self.assertAlmostEqual(m.mcnemar_exact(0, 6), 0.03125)
        self.assertEqual(m.mcnemar_exact(3, 3), 1.0)
        self.assertEqual(m.mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(m.mcnemar_exact(2, 10), 0.03857, places=4)

    def test_bootstrap_deterministic_and_bounds(self):
        a = [True] * 50 + [False] * 50
        b = [True] * 70 + [False] * 30
        d1 = m.paired_bootstrap_diff(a, b)
        self.assertEqual(d1, m.paired_bootstrap_diff(a, b))
        self.assertAlmostEqual(d1[0], 0.2)
        self.assertLess(d1[1], 0.2)
        self.assertGreater(d1[2], 0.2)

    def test_per_class_and_macro_f1(self):
        y_true = ["a", "a", "b", "b"]
        y_pred = ["a", UNMATCHED, "b", "a"]
        stats = m.per_class_stats(y_true, y_pred, ["a", "b"])
        self.assertAlmostEqual(stats["a"].precision, 0.5)
        self.assertAlmostEqual(stats["a"].recall, 0.5)
        self.assertAlmostEqual(stats["b"].precision, 1.0)
        self.assertAlmostEqual(stats["b"].recall, 0.5)
        self.assertAlmostEqual(m.macro_f1(stats), (0.5 + 2 / 3) / 2)

    def test_calibration(self):
        self.assertAlmostEqual(m.expected_calibration_error([1.0, 1.0, 0.0], [True, True, False]), 0.0)
        self.assertAlmostEqual(m.expected_calibration_error([0.9] * 10, [True] * 5 + [False] * 5), 0.4)
        self.assertAlmostEqual(m.brier_score([1.0, 0.0], [True, True]), 0.5)

    def test_selective(self):
        s = m.selective_accuracy([0.9, 0.8, 0.3, 0.6], [True, False, False, True], 0.7)
        self.assertEqual(s["n"], 2)
        self.assertAlmostEqual(s["coverage"], 0.5)
        self.assertAlmostEqual(s["accuracy"], 0.5)

    def test_detection(self):
        d = m.binary_detection([True, True, False, False], [True, False, False, True])
        self.assertEqual((d["sensitivity"], d["specificity"]), (0.5, 0.5))

    def test_derangement(self):
        items = list(range(20))
        out = m.derangement(items)
        self.assertEqual(sorted(out), items)
        self.assertTrue(all(a != b for a, b in zip(items, out)))
        with self.assertRaises(ValueError):
            m.derangement([1])

    def test_weather_window_excludes_capture_day(self):
        self.assertEqual(window_for(date(2026, 10, 14)), (date(2026, 10, 7), date(2026, 10, 13)))


def rec(sample, label, cond, disease, conf=0.9, severity="sedang", repeat=0, crop="cabai", is_plant=True):
    return {
        "key": f"{sample}|{cond}|{repeat}", "sample_id": sample, "crop": crop, "label": label,
        "condition": cond, "repeat": repeat, "result": {
            "is_plant": is_plant, "disease_name": disease, "confidence_score": conf, "severity": severity},
    }


class ScoringTests(unittest.TestCase):
    def test_summary_and_pairing(self):
        records = [
            rec("1", "cabai_cercospora", "no_weather", "Cercospora"),
            rec("2", "cabai_cercospora", "no_weather", "Antraknosa"),
            rec("3", "cabai_sehat", "no_weather", "Sehat", severity="sehat"),
            rec("4", "cabai_antraknosa", "no_weather", "Busuk buah misterius"),
            rec("1", "cabai_cercospora", "weather", "Cercospora"),
            rec("2", "cabai_cercospora", "weather", "Cercospora"),
            rec("3", "cabai_sehat", "weather", "Sehat", severity="sehat"),
            {"key": "4|weather|0", "sample_id": "4", "crop": "cabai", "label": "cabai_antraknosa",
             "condition": "weather", "repeat": 0, "result": None, "error": "boom"},
        ]
        s = compute_summary(records, LABELS)
        nw, w = s["conditions"]["no_weather"], s["conditions"]["weather"]
        self.assertEqual(nw["n"], 4)
        self.assertAlmostEqual(nw["accuracy"], 0.5)
        self.assertAlmostEqual(nw["unmatched_rate"], 0.25)
        self.assertEqual(w["errors"], 1)
        self.assertAlmostEqual(w["accuracy"], 1.0)
        self.assertEqual(nw["detection"]["specificity"], 1.0)

        cmp = s["comparisons"][0]
        self.assertEqual((cmp["a"], cmp["b"], cmp["n_paired"]), ("no_weather", "weather", 3))
        self.assertEqual((cmp["only_a_correct"], cmp["only_b_correct"]), (0, 1))
        self.assertEqual(s["unmatched_names"][0]["disease_name"], "Busuk buah misterius")

    def test_consistency_across_repeats(self):
        records = [
            rec("1", "cabai_cercospora", "no_weather", "Cercospora", repeat=0),
            rec("1", "cabai_cercospora", "no_weather", "Antraknosa", repeat=1),
            rec("2", "cabai_sehat", "no_weather", "Sehat", repeat=0, severity="sehat"),
            rec("2", "cabai_sehat", "no_weather", "Sehat", repeat=1, severity="sehat"),
        ]
        s = compute_summary(records, LABELS)["conditions"]["no_weather"]
        self.assertEqual(s["n"], 2)  # main metrics use repeat 0 only
        self.assertAlmostEqual(s["consistency"]["identical_prediction_rate"], 0.5)


def _jpeg(path: Path, size=(1600, 1200)):
    """Noise image so the JPEG is above the app's 300 KB skip-compression threshold."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3)).save(path, "JPEG", quality=90)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        labels = {"classes": {
            "cabai_sehat": {"crop": "cabai", "healthy": True, "aliases": ["sehat"]},
            "cabai_cercospora": {"crop": "cabai", "aliases": ["cercospora"]},
        }}
        (self.dir / "labels.json").write_text(json.dumps(labels))
        rows = ["path,crop,label,lat,lon,taken_at"]
        for i in range(4):
            label = "cabai_cercospora" if i % 2 else "cabai_sehat"
            _jpeg(self.dir / f"img/{i}.jpg")
            rows.append(f"img/{i}.jpg,cabai,{label},-6.9{i},107.7,2026-10-1{i}")
        _jpeg(self.dir / "img/nogps.jpg")
        rows.append("img/nogps.jpg,cabai,cabai_sehat,,,")
        (self.dir / "manifest.csv").write_text("\n".join(rows) + "\n")
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, **kw):
        base = dict(manifest=str(self.dir / "manifest.csv"), labels=str(self.dir / "labels.json"),
                    out=str(self.dir / "out"), model="fake-model", conditions=list(ev.ALL_CONDITIONS),
                    repeats=1, limit=None, concurrency=2, rpm=0, threshold=0.7, no_compress=False, yes=True)
        base.update(kw)
        return Namespace(**base)

    def _run(self, **kw):
        async def fake_call(client, model, image, mime, prompt):
            self.calls.append((model, mime, len(image), "Data cuaca" in prompt))
            return ds.DiagnosisResult(  # content is irrelevant for the fake
                is_plant=True, disease_name="Sehat", confidence_score=0.8,
                severity="sehat", cause_explanation="-", warning_signs="-", action_steps=["a", "b", "c"],
                urgency="tidak mendesak", estimated_yield_impact="-", preventive_measures="-")

        async def fake_weather(client, lat, lon, taken, days=7):
            return f"7 hari terakhir: lokasi {lat:.2f} tanggal {taken}.", "forecast"

        with patch.object(ds, "_call_gemini", fake_call), \
             patch.object(ev, "weather_context_for_date", fake_weather), \
             patch.object(ev, "make_client", lambda: object()), \
             patch("sys.stdout", new_callable=io.StringIO):
            return asyncio.run(ev.run(self.args(**kw)))

    def test_full_run_resume_and_outputs(self):
        self.assertEqual(self._run(), 0)
        # 5 no_weather + 4 weather + 4 shuffled (the no-GPS photo has no weather)
        self.assertEqual(len(self.calls), 13)
        self.assertEqual(sum(1 for c in self.calls if c[3]), 8)
        self.assertTrue(all(c[1] == "image/jpeg" for c in self.calls))

        out = self.dir / "out"
        for name in ("config.json", "raw.jsonl", "summary.json", "report.md", "predictions.csv", "weather_cache.json"):
            self.assertTrue((out / name).exists(), name)
        summary = json.loads((out / "summary.json").read_text())
        self.assertEqual(summary["conditions"]["no_weather"]["n"], 5)
        self.assertEqual(summary["conditions"]["weather"]["n"], 4)
        self.assertEqual(len(summary["comparisons"]), 3)

        shuffled = [json.loads(l) for l in (out / "raw.jsonl").read_text().splitlines()]
        real = {r["sample_id"]: r["weather_context"] for r in shuffled if r["condition"] == "weather"}
        for r in shuffled:
            if r["condition"] == "weather_shuffled":
                self.assertNotEqual(r["weather_context"], real[r["sample_id"]])

        # Resume: nothing new to call
        self.calls.clear()
        self.assertEqual(self._run(), 0)
        self.assertEqual(self.calls, [])

        # Extra repeat only calls the new repeat
        self._run(repeats=2)
        self.assertEqual(len(self.calls), 13)

    def test_daily_quota_stops_run_and_resumes_later(self):
        from google.genai import errors as genai_errors
        daily = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota", "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                {"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                 "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaValue": "20"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "33s"}]}}
        calls = []

        async def quota_after_two(client, model, image, mime, prompt):
            calls.append(1)
            if len(calls) > 2:
                raise genai_errors.APIError(429, daily)
            return ds.DiagnosisResult(
                is_plant=True, disease_name="Sehat", confidence_score=0.8, severity="sehat",
                cause_explanation="-", warning_signs="-", action_steps=["a"], urgency="tidak mendesak",
                estimated_yield_impact="-", preventive_measures="-")

        with patch.object(ds, "_call_gemini", quota_after_two), \
             patch.object(ev, "make_client", lambda: object()), \
             patch("sys.stdout", new_callable=io.StringIO) as out:
            code = asyncio.run(ev.run(self.args(conditions=["no_weather"], concurrency=1)))
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 3)  # no pointless retries on a daily quota
        self.assertIn("Kuota harian", out.getvalue())

        # Next day: only the remaining samples are called
        self.calls.clear()
        self._run(conditions=["no_weather"])
        self.assertEqual(len(self.calls), 3)

    def test_describe_quota(self):
        from google.genai import errors as genai_errors
        per_minute = {"error": {"code": 429, "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                {"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier", "quotaValue": "10"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "12s"}]}}
        scope, retry, desc = ev.describe_quota(genai_errors.APIError(429, per_minute))
        self.assertEqual((scope, retry), ("minute", 12.0))
        self.assertIn("batas 10", desc)
        self.assertEqual(ev.describe_quota(genai_errors.APIError(429, {"error": {"message": "x"}}))[:2], (None, None))

    def test_refuses_to_mix_models(self):
        self._run(conditions=["no_weather"], limit=2)
        with self.assertRaises(SystemExit):
            self._run(model="other-model")

    def test_limit_is_label_balanced(self):
        self._run(conditions=["no_weather"], limit=2)
        labels = [json.loads(l)["label"] for l in (self.dir / "out" / "raw.jsonl").read_text().splitlines()]
        self.assertEqual(sorted(labels), ["cabai_cercospora", "cabai_sehat"])

    def test_manifest_validation(self):
        (self.dir / "manifest.csv").write_text("path,crop,label\nimg/missing.jpg,cabai,cabai_sehat\nimg/0.jpg,padi,cabai_sehat\nimg/1.jpg,cabai,unknown\n")
        with self.assertRaises(SystemExit) as ctx:
            ev.load_manifest(self.dir / "manifest.csv", ev.load_labels(self.dir / "labels.json"))
        msg = str(ctx.exception)
        self.assertIn("tidak ditemukan", msg)
        self.assertIn("milik tanaman", msg)
        self.assertIn("tidak ada di labels.json", msg)

    def test_prepare_image_matches_app(self):
        big = self.dir / "img/0.jpg"
        data, mime = ev.prepare_image(big, compress=True)
        with Image.open(io.BytesIO(data)) as img:
            self.assertLessEqual(max(img.size), 1024)
        self.assertEqual(mime, "image/jpeg")
        small = self.dir / "small.png"
        Image.new("RGB", (64, 64)).save(small, "PNG")
        data, mime = ev.prepare_image(small, compress=True)
        self.assertEqual((data, mime), (small.read_bytes(), "image/png"))


if __name__ == "__main__":
    unittest.main()
