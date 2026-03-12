from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings


def resolve_resources_dir(explicit: str | None = None) -> Path | None:
    candidates: list[Path] = []

    if explicit:
        raw = Path(explicit).expanduser()
        candidates.extend([raw, settings.BASE_DIR / raw, settings.BASE_DIR.parent / raw])

    candidates.extend(
        [
            settings.BASE_DIR.parent / "resources",
            settings.BASE_DIR / "resources",
        ]
    )

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return None


def resolve_uzbekistan_data_dir(explicit: str | None = None) -> Path | None:
    candidates: list[Path] = []

    if explicit:
        raw = Path(explicit).expanduser()
        candidates.extend([raw, settings.BASE_DIR / raw, settings.BASE_DIR.parent / raw])

    resources_dir = resolve_resources_dir()
    if resources_dir:
        candidates.extend(
            [
                resources_dir / "uzbekistan-regions-data-master" / "JSON",
                resources_dir / "uzbekistan-regions-data-master",
                resources_dir,
            ]
        )

    for candidate in candidates:
        if not candidate.exists() or not candidate.is_dir():
            continue
        if (candidate / "regions.json").exists():
            return candidate.resolve()
        nested = candidate / "uzbekistan-regions-data-master" / "JSON"
        if nested.exists() and nested.is_dir():
            return nested.resolve()
    return None


def load_json_records(data_dir: Path, filename: str) -> list[dict]:
    target = data_dir / filename
    with target.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{target} must contain a JSON list.")
    return data


def make_uz_slug(name: str) -> str:
    replacements = {
        "ʻ": "",
        "ʼ": "",
        "'": "",
        "’": "",
        "ў": "o",
        "ғ": "g",
        "қ": "q",
        "ҳ": "h",
        "Ў": "O",
        "Ғ": "G",
        "Қ": "Q",
        "Ҳ": "H",
        " ": "-",
    }

    slug = (name or "").strip().lower()
    for old, new in replacements.items():
        slug = slug.replace(old, new)

    slug = "".join(char if char.isalnum() or char == "-" else "-" for char in slug)
    slug = "-".join(part for part in slug.split("-") if part)
    return slug[:255]
