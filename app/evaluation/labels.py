"""
Ground-truth label set and mapping of free-text model output to label classes.

The model answers with a free-text Indonesian disease name ("Bercak daun Cercospora",
"Hawar Daun Bakteri (Kresek)"). Each class in labels.json lists aliases; a prediction
maps to the single class of the same crop whose aliases appear in the name.
Unmapped answers are kept as UNMATCHED for manual review instead of being guessed.
"""
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

INVALID = "__invalid__"      # model said the photo is not a usable plant photo
UNMATCHED = "__unmatched__"  # disease name matches no alias of this crop
AMBIGUOUS = "__ambiguous__"  # equally strong matches for two different classes


@dataclass(frozen=True)
class LabelClass:
    id: str
    crop: str
    healthy: bool
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class LabelSet:
    classes: dict[str, LabelClass]

    def for_crop(self, crop: str) -> list[LabelClass]:
        crop = normalize_text(crop)
        return [c for c in self.classes.values() if normalize_text(c.crop) == crop]

    def is_healthy(self, class_id: str) -> bool:
        c = self.classes.get(class_id)
        return bool(c and c.healthy)


def normalize_text(text: Optional[str]) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return text.strip()


def load_labels(path: str | Path) -> LabelSet:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_classes = data.get("classes")
    if not isinstance(raw_classes, dict) or not raw_classes:
        raise ValueError(f"{path}: 'classes' must be a non-empty object")

    classes: dict[str, LabelClass] = {}
    for class_id, spec in raw_classes.items():
        if class_id.startswith("__"):
            raise ValueError(f"{path}: class id {class_id!r} is reserved")
        crop = spec.get("crop")
        if not crop:
            raise ValueError(f"{path}: class {class_id!r} has no 'crop'")
        aliases = tuple(a for a in (normalize_text(x) for x in spec.get("aliases", [])) if a)
        if not aliases:
            raise ValueError(f"{path}: class {class_id!r} needs at least one alias")
        classes[class_id] = LabelClass(class_id, crop, bool(spec.get("healthy", False)), aliases)
    return LabelSet(classes)


def match_prediction(
    labels: LabelSet, crop: str, disease_name: Optional[str], is_plant: bool = True
) -> tuple[str, Optional[str]]:
    """
    Returns (class_id or INVALID/UNMATCHED/AMBIGUOUS, matched alias).
    Only the disease_name is used: crediting words from the explanation would reward hedging.
    An alias nested inside a longer matching alias is ignored; matches for two different
    classes that remain make the answer AMBIGUOUS (counted as wrong).
    """
    if not is_plant:
        return INVALID, None

    text = f" {normalize_text(disease_name)} "
    # Every alias occurrence as a character span (whole words only).
    hits: list[tuple[int, int, str, str]] = []
    for cls in labels.for_crop(crop):
        for alias in cls.aliases:
            needle = f" {alias} "
            pos = text.find(needle)
            while pos != -1:
                hits.append((pos + 1, pos + 1 + len(alias), cls.id, alias))
                pos = text.find(needle, pos + 1)

    # Drop hits nested inside a longer hit ("bercak daun" inside "bercak daun bakteri").
    kept = [
        h for h in hits
        if not any(o is not h and o[0] <= h[0] and h[1] <= o[1] and (o[1] - o[0]) > (h[1] - h[0]) for o in hits)
    ]
    best: dict[str, str] = {}
    for _, _, class_id, alias in sorted(kept, key=lambda h: h[1] - h[0], reverse=True):
        best.setdefault(class_id, alias)

    # Two different classes left means a hedged answer ("antraknosa atau bercak daun"): not credited.
    if not best:
        return UNMATCHED, None
    if len(best) > 1:
        return AMBIGUOUS, None
    class_id, alias = next(iter(best.items()))
    return class_id, alias
