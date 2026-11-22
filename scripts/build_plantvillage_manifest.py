"""
Build data/eval/manifest.csv and data/eval/labels.json from a PlantVillage folder
(Kaggle 15-class version: tomato, potato, bell pepper).

Usage (from the project root):
    python scripts/build_plantvillage_manifest.py --root data/eval/images/PlantVillage --per-class 30

- Samples a fixed number of images per class (seeded), so classes are balanced and the
  run fits a free-tier quota.
- Skips the nested duplicate folder (PlantVillage/PlantVillage/...) and non-image files,
  and drops byte-identical duplicates.
- No lat/lon/taken_at: PlantVillage has no location or date, so only the no_weather
  condition is valid on this dataset.
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, UnidentifiedImageError  # noqa: E402

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}

# folder name -> (class id, crop given to the model, healthy, aliases)
# Aliases: Indonesian names the model tends to use, English names, pathogen names.
# Deliberately no generic aliases such as "bercak daun" or "hawar daun": they would
# match several classes and hide real confusions.
FOLDERS = {
    "Pepper__bell___Bacterial_spot": ("paprika_bercak_bakteri", "paprika", False,
        ["bercak bakteri", "bercak daun bakteri", "xanthomonas", "bacterial spot", "bacterial leaf spot"]),
    "Pepper__bell___healthy": ("paprika_sehat", "paprika", True, ["sehat"]),
    "Potato___Early_blight": ("kentang_hawar_awal", "kentang", False,
        ["bercak kering", "early blight", "alternaria", "hawar awal", "bercak alternaria", "hawar daun alternaria"]),
    "Potato___Late_blight": ("kentang_hawar_akhir", "kentang", False,
        ["busuk daun", "hawar daun phytophthora", "phytophthora", "late blight", "hawar akhir", "lodoh"]),
    "Potato___healthy": ("kentang_sehat", "kentang", True, ["sehat"]),
    "Tomato_Bacterial_spot": ("tomat_bercak_bakteri", "tomat", False,
        ["bercak bakteri", "bercak daun bakteri", "xanthomonas", "bacterial spot", "bacterial leaf spot"]),
    "Tomato_Early_blight": ("tomat_hawar_awal", "tomat", False,
        ["bercak kering", "early blight", "alternaria", "hawar awal", "bercak alternaria", "hawar daun alternaria"]),
    "Tomato_Late_blight": ("tomat_hawar_akhir", "tomat", False,
        ["busuk daun", "hawar daun phytophthora", "phytophthora", "late blight", "hawar akhir", "lodoh"]),
    "Tomato_Leaf_Mold": ("tomat_jamur_daun", "tomat", False,
        ["jamur daun", "kapang daun", "leaf mold", "leaf mould", "cladosporium", "fulvia", "passalora"]),
    "Tomato_Septoria_leaf_spot": ("tomat_bercak_septoria", "tomat", False,
        ["septoria", "bercak daun septoria", "septoria leaf spot"]),
    "Tomato_Spider_mites_Two_spotted_spider_mite": ("tomat_tungau", "tomat", False,
        ["tungau", "tungau laba laba", "tungau merah", "spider mite", "spider mites", "tetranychus"]),
    "Tomato__Target_Spot": ("tomat_bercak_target", "tomat", False,
        ["bercak target", "target spot", "corynespora"]),
    "Tomato__Tomato_YellowLeaf__Curl_Virus": ("tomat_virus_keriting_kuning", "tomat", False,
        ["keriting kuning", "daun keriting kuning", "virus kuning", "yellow leaf curl", "tylcv", "begomovirus", "virus gemini"]),
    "Tomato__Tomato_mosaic_virus": ("tomat_virus_mosaik", "tomat", False,
        ["mosaik", "mozaik", "mosaic", "virus mosaik", "tomv", "tobamovirus"]),
    "Tomato_healthy": ("tomat_sehat", "tomat", True, ["sehat"]),
}


def is_readable_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except (UnidentifiedImageError, OSError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default="data/eval/images/PlantVillage")
    parser.add_argument("--per-class", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--manifest", default="data/eval/manifest.csv")
    parser.add_argument("--labels", default="data/eval/labels.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve()
    if not root.is_dir():
        raise SystemExit(f"Folder tidak ditemukan: {root}")

    class_dirs = sorted(d for d in root.iterdir() if d.is_dir() and d.name in FOLDERS)
    unknown = sorted(d.name for d in root.iterdir() if d.is_dir() and d.name not in FOLDERS and d.name != root.name)
    if unknown:
        print(f"Peringatan: folder tanpa pemetaan dilewati: {', '.join(unknown)}")
    if root.joinpath(root.name).is_dir():
        print(f"Folder duplikat {root.name}/{root.name}/ dilewati.")
    if not class_dirs:
        raise SystemExit("Tidak ada folder kelas yang dikenali.")

    rng = random.Random(args.seed)
    seen_hashes: set[str] = set()
    rows, report = [], []
    for d in class_dirs:
        class_id, crop, _, _ = FOLDERS[d.name]
        files = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
        rng.shuffle(files)
        picked, skipped_dup, skipped_bad = [], 0, 0
        for p in files:
            if len(picked) >= args.per_class:
                break
            digest = hashlib.sha1(p.read_bytes()).hexdigest()
            if digest in seen_hashes:
                skipped_dup += 1
                continue
            if not is_readable_image(p):
                skipped_bad += 1
                continue
            seen_hashes.add(digest)
            picked.append(p)
        for p in picked:
            rows.append({"path": os.path.relpath(p, manifest_path.parent).replace(os.sep, "/"),
                         "crop": crop, "label": class_id, "lat": "", "lon": "", "taken_at": ""})
        report.append((class_id, len(files), len(picked), skipped_dup, skipped_bad))

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "crop", "label", "lat", "lon", "taken_at"])
        writer.writeheader()
        writer.writerows(rows)

    labels = {
        "_catatan": "Dibuat oleh scripts/build_plantvillage_manifest.py. Tambah alias dari report.md setelah dicek manual, lalu jalankan `score` lagi.",
        "classes": {cid: {"crop": crop, "healthy": healthy, "aliases": aliases}
                    for cid, crop, healthy, aliases in FOLDERS.values()},
    }
    Path(args.labels).write_text(json.dumps(labels, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'kelas':32s} {'tersedia':>8s} {'diambil':>8s} {'duplikat':>8s} {'rusak':>6s}")
    for cid, total, picked, dup, bad in report:
        flag = "  <- kurang dari --per-class" if picked < args.per_class else ""
        print(f"{cid:32s} {total:8d} {picked:8d} {dup:8d} {bad:6d}{flag}")
    print(f"\n{len(rows)} gambar -> {args.manifest}\nlabel -> {args.labels}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
