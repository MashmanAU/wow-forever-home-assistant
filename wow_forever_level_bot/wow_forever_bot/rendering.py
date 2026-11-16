from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import ImageDraw, ImageFont

from .models import SnapshotProgress

DARK_THEME = {
    "background": "#0d1018",
    "card": "#171b24",
    "card_alt": "#1c212c",
    "border": "#323a49",
    "gold": "#d8ad55",
    "text": "#f2f3f5",
    "muted": "#adb4c0",
    "track": "#343b49",
}

PROFESSION_SHORT = {
    "alchemy": "AL",
    "archaeology": "AR",
    "blacksmithing": "BS",
    "cooking": "CO",
    "enchanting": "EN",
    "engineering": "EG",
    "first aid": "FA",
    "fishing": "FI",
    "herbalism": "HB",
    "inscription": "IN",
    "jewelcrafting": "JC",
    "leatherworking": "LW",
    "mining": "MI",
    "skinning": "SK",
    "tailoring": "TA",
}


def _font_path(*names: str) -> str | None:
    roots = (
        Path("/usr/share/fonts/TTF"),
        Path("/usr/share/fonts/dejavu"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/dejavu-sans-fonts"),
        Path("/usr/share/fonts/liberation"),
        Path(__file__).with_name("assets") / "fonts",
    )
    for root in roots:
        for name in names:
            path = root / name
            if path.exists():
                return str(path)
    return None


def _font(
    size: int,
    *,
    bold: bool = False,
    condensed: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if condensed:
        names = (
            "DejaVuSansCondensed-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "DejaVuSansCondensed.ttf",
            "DejaVuSans.ttf",
        ) if bold else (
            "DejaVuSansCondensed.ttf",
            "DejaVuSans.ttf",
            "DejaVuSansCondensed-Bold.ttf",
            "DejaVuSans-Bold.ttf",
        )
    else:
        names = ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf") if bold else (
            "DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf",
        )
    path = _font_path(*names)
    if path is None:
        raise RuntimeError("A scalable DejaVu Sans font is required for image rendering")
    return ImageFont.truetype(path, size=size)


def _opt(options: Any, name: str, default: Any) -> Any:
    return getattr(options, name, default)


def _fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    width: int,
) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    suffix = "…"
    candidate = text
    while candidate and draw.textlength(candidate + suffix, font=font) > width:
        candidate = candidate[:-1]
    return candidate.rstrip() + suffix


def _profession_text(row: SnapshotProgress, options: Any) -> str:
    if not _opt(options, "show_professions", True):
        return ""
    seen: set[str] = set()
    values: list[str] = []
    for profession in row.snapshot.professions:
        key = profession.profession_name.casefold()
        if key in seen:
            continue
        seen.add(key)
        if _opt(options, "show_profession_icons", True):
            label = PROFESSION_SHORT.get(key, profession.profession_name[:2].upper())
        else:
            label = profession.profession_name
        value = f"{label} {profession.skill_points:,}"
        if profession.max_skill_points is not None:
            value += f"/{profession.max_skill_points:,}"
        values.append(value)
        if len(values) >= 2:
            break
    return "  •  ".join(values)
