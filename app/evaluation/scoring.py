"""
Turns raw model outputs (raw.jsonl) into metrics and a Markdown report.
Scoring is separate from inference, so aliases can be fixed and results re-scored
without calling the model again.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Optional

from app.evaluation.labels import AMBIGUOUS, INVALID, UNMATCHED, LabelSet, match_prediction
from app.evaluation import metrics as m

CONDITION_ORDER = ["no_weather", "weather", "weather_shuffled"]
CONDITION_LABEL = {
    "no_weather": "Tanpa cuaca",
    "weather": "Dengan cuaca asli",
    "weather_shuffled": "Cuaca acak (kontrol plasebo)",
}
COMPARISONS = [
    ("no_weather", "weather", "Efek menambahkan cuaca"),
    ("weather_shuffled", "weather", "Informasi cuaca vs sekadar prompt lebih panjang"),
    ("no_weather", "weather_shuffled", "Efek prompt cuaca yang tidak relevan"),
]
SMALL_CLASS = 30


def load_records(path: Path) -> list[dict]:
    """Latest record per key wins, so a successful retry replaces an earlier error."""
    latest: dict[str, dict] = {}
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                if rec.get("result") is not None or rec["key"] not in latest:
                    latest[rec["key"]] = rec
    return list(latest.values())


def score_record(rec: dict, labels: LabelSet) -> dict:
    res = rec["result"]
    pred, alias = match_prediction(labels, rec["crop"], res.get("disease_name"), res.get("is_plant", True))
    true_diseased = not labels.is_healthy(rec["label"])
    pred_diseased = bool(res.get("is_plant", True)) and res.get("severity") != "sehat"
    return {
        **rec,
        "pred": pred,
        "matched_alias": alias,
        "correct": pred == rec["label"],
        "true_diseased": true_diseased,
        "pred_diseased": pred_diseased,
        "confidence": float(res.get("confidence_score", 0.0)),
    }


def _condition_metrics(rows: list[dict], labels: LabelSet, threshold: float) -> dict:
    y_true = [r["label"] for r in rows]
    y_pred = [r["pred"] for r in rows]
    correct = [r["correct"] for r in rows]
    conf = [r["confidence"] for r in rows]
    n = len(rows)
    acc = sum(correct) / n if n else None
    classes = sorted({*y_true})
    stats = m.per_class_stats(y_true, y_pred, classes)
    return {
        "n": n,
        "accuracy": acc,
        "accuracy_ci95": m.wilson_interval(sum(correct), n),
        "macro_f1": m.macro_f1(stats),
        "per_class": {c: vars(s) for c, s in stats.items()},
        "confusion": m.confusion_matrix(y_true, y_pred),
        "detection": m.binary_detection([r["true_diseased"] for r in rows], [r["pred_diseased"] for r in rows]),
        "invalid_rate": y_pred.count(INVALID) / n if n else None,
        "unmatched_rate": y_pred.count(UNMATCHED) / n if n else None,
        "ambiguous_rate": y_pred.count(AMBIGUOUS) / n if n else None,
        "ece": m.expected_calibration_error(conf, correct),
        "brier": m.brier_score(conf, correct),
        "reliability": m.reliability_table(conf, correct),
        "selective": m.selective_accuracy(conf, correct, threshold),
    }


def _consistency(rows: list[dict]) -> Optional[dict]:
    by_sample: dict[str, set] = defaultdict(set)
    counts: Counter = Counter()
    for r in rows:
        by_sample[r["sample_id"]].add(r["pred"])
        counts[r["sample_id"]] += 1
    multi = [s for s, c in counts.items() if c > 1]
    if not multi:
        return None
    stable = sum(1 for s in multi if len(by_sample[s]) == 1)
    return {"samples_with_repeats": len(multi), "identical_prediction_rate": stable / len(multi)}


def compute_summary(records: Iterable[dict], labels: LabelSet, threshold: float = 0.7) -> dict:
    records = list(records)
    ok = [score_record(r, labels) for r in records if r.get("result") is not None]
    errors = Counter(r["condition"] for r in records if r.get("result") is None)

    by_cond: dict[str, list[dict]] = defaultdict(list)
    for r in ok:
        by_cond[r["condition"]].append(r)

    conditions = {}
    for cond in [c for c in CONDITION_ORDER if c in by_cond] + sorted(set(by_cond) - set(CONDITION_ORDER)):
        rows = by_cond[cond]
        first = [r for r in rows if r["repeat"] == 0]
        conditions[cond] = {
            **_condition_metrics(first, labels, threshold),
            "errors": errors.get(cond, 0),
            "consistency": _consistency(rows),
        }

    comparisons = []
    for a, b, title in COMPARISONS:
        if a not in by_cond or b not in by_cond:
            continue
        ra = {r["sample_id"]: r["correct"] for r in by_cond[a] if r["repeat"] == 0}
        rb = {r["sample_id"]: r["correct"] for r in by_cond[b] if r["repeat"] == 0}
        common = sorted(set(ra) & set(rb))
        if not common:
            continue
        xa, xb = [ra[s] for s in common], [rb[s] for s in common]
        b_cnt = sum(x and not y for x, y in zip(xa, xb))  # a right, b wrong
        c_cnt = sum((not x) and y for x, y in zip(xa, xb))  # a wrong, b right
        diff, lo, hi = m.paired_bootstrap_diff(xa, xb)
        comparisons.append({
            "a": a, "b": b, "title": title, "n_paired": len(common),
            "accuracy_a": sum(xa) / len(xa), "accuracy_b": sum(xb) / len(xb),
            "diff": diff, "diff_ci95": (lo, hi),
            "only_a_correct": b_cnt, "only_b_correct": c_cnt,
            "mcnemar_p": m.mcnemar_exact(b_cnt, c_cnt),
        })

    unmatched = Counter(
        (r["crop"], r["result"].get("disease_name", "")) for r in ok if r["pred"] in (UNMATCHED, AMBIGUOUS)
    )
    return {
        "threshold": threshold,
        "n_records": len(records),
        "n_scored": len(ok),
        "label_distribution": dict(Counter(r["label"] for r in ok if r["condition"] == "no_weather" and r["repeat"] == 0)),
        "conditions": conditions,
        "comparisons": comparisons,
        "unmatched_names": [{"crop": c, "disease_name": d, "count": n} for (c, d), n in unmatched.most_common()],
        "scored_rows": ok,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _pct(x: Optional[float]) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def _num(x: Optional[float], digits: int = 3) -> str:
    return "-" if x is None else f"{x:.{digits}f}"


def render_markdown(summary: dict, config: dict) -> str:
    out = [
        "# Evaluasi diagnosis FarmLens",
        "",
        f"- Model: `{config.get('model')}` (tanpa fallback, supaya hasil tidak tercampur antar-model)",
        f"- Versi prompt: `{config.get('prompt_version')}`",
        f"- Dataset: `{config.get('manifest')}`",
        f"- Gambar dikompres seperti di aplikasi: {'ya' if config.get('compress') else 'tidak'}",
        f"- Record: {summary['n_scored']} berhasil dari {summary['n_records']}",
        "",
        "## Ringkasan per kondisi",
        "",
        "| Kondisi | n | Akurasi (95% CI) | Macro-F1 | Sensitivitas | Spesifisitas | Tidak cocok alias | Foto ditolak | ECE | Error API |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cond, s in summary["conditions"].items():
        lo, hi = s["accuracy_ci95"]
        out.append(
            f"| {CONDITION_LABEL.get(cond, cond)} | {s['n']} | {_pct(s['accuracy'])} ({_pct(lo)}-{_pct(hi)}) "
            f"| {_num(s['macro_f1'])} | {_pct(s['detection']['sensitivity'])} | {_pct(s['detection']['specificity'])} "
            f"| {_pct(s['unmatched_rate'])} | {_pct(s['invalid_rate'])} | {_num(s['ece'])} | {s['errors']} |"
        )

    if summary["comparisons"]:
        out += [
            "",
            "## Perbandingan berpasangan (gambar yang sama)",
            "",
            "| Perbandingan | n | Akurasi A | Akurasi B | Selisih B-A (95% CI bootstrap) | Hanya A benar | Hanya B benar | p McNemar |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in summary["comparisons"]:
            lo, hi = c["diff_ci95"]
            out.append(
                f"| {c['title']}: {CONDITION_LABEL[c['a']]} (A) vs {CONDITION_LABEL[c['b']]} (B) | {c['n_paired']} "
                f"| {_pct(c['accuracy_a'])} | {_pct(c['accuracy_b'])} | {100 * c['diff']:+.1f} pp ({100 * lo:+.1f} s/d {100 * hi:+.1f}) "
                f"| {c['only_a_correct']} | {c['only_b_correct']} | {_num(c['mcnemar_p'])} |"
            )
        out += [
            "",
            "Cara membaca: klaim \"cuaca meningkatkan akurasi\" baru didukung jika *Dengan cuaca asli* lebih baik dari "
            "*Tanpa cuaca* **dan** dari *Cuaca acak*. Kalau cuaca acak sama baiknya, kenaikan berasal dari perubahan "
            "prompt, bukan dari informasi cuacanya. CI yang melewati 0 berarti selisihnya belum terbukti.",
        ]

    out += ["", "## Per kelas", ""]
    for cond, s in summary["conditions"].items():
        out += [f"### {CONDITION_LABEL.get(cond, cond)}", "", "| Kelas | Support | Precision | Recall | F1 |", "|---|---|---|---|---|"]
        for cls, st in sorted(s["per_class"].items()):
            flag = " ⚠️" if st["support"] < SMALL_CLASS else ""
            out.append(f"| {cls}{flag} | {st['support']} | {_pct(st['precision'])} | {_pct(st['recall'])} | {_num(st['f1'])} |")
        sel = s["selective"]
        out += [
            "",
            f"Kalibrasi: ECE {_num(s['ece'])}, Brier {_num(s['brier'])}. Jawaban dengan confidence ≥ {sel['threshold']} "
            f"(tidak diberi peringatan di aplikasi): {_pct(sel['coverage'])} dari semua jawaban, akurasinya {_pct(sel['accuracy'])}.",
        ]
        if s.get("consistency"):
            out.append(
                f"Konsistensi antar-ulangan: {_pct(s['consistency']['identical_prediction_rate'])} gambar "
                f"mendapat prediksi yang sama di semua ulangan."
            )
        out.append("")

    if summary["unmatched_names"]:
        out += [
            "## Nama penyakit yang tidak cocok dengan alias",
            "",
            "Cek manual: kalau sebenarnya benar, tambahkan sebagai alias di labels.json lalu jalankan `score` lagi "
            "(tanpa memanggil model). Kalau memang salah, biarkan.",
            "",
            "| Tanaman | Jawaban model | Jumlah |",
            "|---|---|---|",
        ]
        out += [f"| {u['crop']} | {u['disease_name']} | {u['count']} |" for u in summary["unmatched_names"][:50]]

    out += [
        "",
        "## Batasan metodologi",
        "",
        f"- Kelas bertanda ⚠️ punya kurang dari {SMALL_CLASS} gambar; angka per kelasnya sangat tidak stabil.",
        "- Akurasi hanya berlaku untuk distribusi dataset ini. Foto laboratorium (latar polos, satu daun) "
        "biasanya jauh lebih mudah daripada foto lapangan dari HP petani.",
        "- Dataset publik mungkin sudah pernah dilihat model saat pelatihan (kontaminasi), sehingga akurasinya bisa terlalu optimistis.",
        "- Pencocokan nama penyakit memakai alias. Nama yang tidak cocok dihitung salah sampai diperiksa manual.",
        "- Cuaca berasal dari model Open-Meteo, bukan stasiun di lahan.",
        "- Model dipanggil dengan temperature 0.2, jadi hasilnya tidak sepenuhnya deterministik. Pakai `--repeats` untuk mengukur variasinya.",
    ]
    return "\n".join(out) + "\n"


def write_outputs(summary: dict, config: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = summary["scored_rows"]
    with (out_dir / "predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sample_id", "crop", "condition", "repeat", "label", "pred", "correct",
                    "disease_name", "confidence", "severity", "matched_alias", "weather_context"])
        for r in sorted(rows, key=lambda r: (r["sample_id"], r["condition"], r["repeat"])):
            res = r["result"]
            w.writerow([r["sample_id"], r["crop"], r["condition"], r["repeat"], r["label"], r["pred"],
                        int(r["correct"]), res.get("disease_name"), r["confidence"], res.get("severity"),
                        r["matched_alias"] or "", r.get("weather_context") or ""])
    public = {k: v for k, v in summary.items() if k != "scored_rows"}
    (out_dir / "summary.json").write_text(json.dumps(public, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "report.md").write_text(render_markdown(summary, config), encoding="utf-8")
