from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .models import SnapshotProgress
from .presentation import CLASS_COLOURS

THEMES = {
    "dark_warcraft": {
        "background": "#0d1018",
        "header": "#171d2a",
        "card": "#171b24",
        "card_alt": "#1c212c",
        "border": "#323a49",
        "gold": "#d8ad55",
        "text": "#f2f3f5",
        "muted": "#adb4c0",
        "track": "#343b49",
        "progress": "#d8ad55",
    },
    "parchment": {
        "background": "#21180f",
        "header": "#3a2817",
        "card": "#ead8b4",
        "card_alt": "#dfcaa1",
        "border": "#7a5b32",
        "gold": "#f0c563",
        "text": "#2a2118",
        "muted": "#665640",
        "track": "#bda77f",
        "progress": "#8b5a24",
    },
    "minimal": {
        "background": "#f3f4f6",
        "header": "#ffffff",
        "card": "#ffffff",
        "card_alt": "#f9fafb",
        "border": "#d1d5db",
        "gold": "#9a6b12",
        "text": "#111827",
        "muted": "#667085",
        "track": "#e5e7eb",
        "progress": "#5865f2",
    },
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
        Path("/usr/share/fonts/truetype/dejavu"),
        Path(__file__).with_name("assets") / "fonts",
    )
    for root in roots:
        for name in names:
            path = root / name
            if path.exists():
                return str(path)
    return None


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf") if bold else (
        "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
    )
    path = _font_path(*names)
    return ImageFont.truetype(path, size=size) if path else ImageFont.load_default()


def _opt(options: Any, name: str, default: Any) -> Any:
    return getattr(options, name, default)


def _fit(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> str:
    if draw.textlength(text, font=font) <= width:
        return text
    suffix = "…"
    candidate = text
    while candidate and draw.textlength(candidate + suffix, font=font) > width:
        candidate = candidate[:-1]
    return candidate.rstrip() + suffix


def _context(row: SnapshotProgress, options: Any) -> str:
    values: list[str] = []
    if _opt(options, "show_race", True) and row.snapshot.race:
        values.append(row.snapshot.race)
    if _opt(options, "show_class", True) and row.snapshot.character_class:
        values.append(row.snapshot.character_class)
    return " ".join(values)


def _profession_text(row: SnapshotProgress, options: Any) -> str:
    if not _opt(options, "show_professions", True):
        return ""
    limit = {"compact": 1, "standard": 2, "detailed": 3}.get(
        _opt(options, "leaderboard_density", "standard"), 2
    )
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
        if len(values) >= limit:
            break
    return "  •  ".join(values)


def _change_text(row: SnapshotProgress, options: Any) -> str:
    values: list[str] = []
    if _opt(options, "show_24h_changes", True):
        changes: list[str] = []
        if row.levels_24h:
            changes.append(f"Lv {row.levels_24h:+d}")
        if row.deaths_24h:
            changes.append(f"Deaths {row.deaths_24h:+d}")
        if row.profession_skill_gains_24h:
            name, gain = row.profession_skill_gains_24h[0]
            changes.append(f"{PROFESSION_SHORT.get(name.casefold(), name[:2].upper())} {gain:+d}")
        if changes:
            values.append("24h " + ", ".join(changes))
    if _opt(options, "show_7d_changes", False) and row.levels_7d:
        values.append(f"7d Lv {row.levels_7d:+d}")
    if _opt(options, "show_notable_activity", True) and row.new_achievements_24h:
        name = row.new_achievements_24h[0].name or str(row.new_achievements_24h[0].achievement_id)
        values.append("Achievement: " + name)
    return "  •  ".join(values)


def _draw_card(
    draw: ImageDraw.ImageDraw,
    row: SnapshotProgress,
    options: Any,
    theme: dict[str, str],
    box: tuple[int, int, int, int],
    index: int,
) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(
        box,
        radius=18,
        fill=theme["card_alt"] if index % 2 else theme["card"],
        outline=theme["border"],
        width=2,
    )
    name_font = _font(28, bold=True)
    meta_font = _font(19)
    small_font = _font(17)
    rank_font = _font(19, bold=True)
    cursor_x = x1 + 20

    if _opt(options, "show_rank", True) and row.rank is not None:
        badge = (cursor_x, y1 + 18, cursor_x + 44, y1 + 62)
        rank_fill = theme["gold"] if row.rank <= 3 else theme["border"]
        draw.ellipse(badge, fill=rank_fill)
        rank_text = str(row.rank)
        rank_colour = "#17130b" if row.rank <= 3 else theme["text"]
        bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
        draw.text(
            (cursor_x + 22 - (bbox[2] - bbox[0]) / 2, y1 + 39 - (bbox[3] - bbox[1]) / 2),
            rank_text,
            font=rank_font,
            fill=rank_colour,
        )
        cursor_x += 56

    class_name = row.snapshot.character_class or ""
    class_hex = CLASS_COLOURS.get(class_name.casefold(), 0x5865F2)
    class_colour = f"#{class_hex:06x}"
    if _opt(options, "show_class_icons", True) and class_name:
        badge = (cursor_x, y1 + 18, cursor_x + 44, y1 + 62)
        draw.rounded_rectangle(badge, radius=10, fill=class_colour)
        label = "".join(word[0] for word in class_name.split())[:2].upper()
        bbox = draw.textbbox((0, 0), label, font=small_font)
        draw.text(
            (cursor_x + 22 - (bbox[2] - bbox[0]) / 2, y1 + 39 - (bbox[3] - bbox[1]) / 2),
            label,
            font=small_font,
            fill="#0b0d12",
        )
        cursor_x += 56

    name_colour = class_colour if _opt(options, "use_class_colours", True) else theme["text"]
    right_text: list[str] = []
    if _opt(options, "show_level", True):
        right_text.append(f"LEVEL {row.snapshot.level}/60")
    if _opt(options, "show_lifetime_deaths", True):
        deaths = row.snapshot.deaths.lifetime
        right_text.append(f"DEATHS {deaths:,}" if deaths is not None else "DEATHS —")
    right = "   ".join(right_text)
    right_width = int(draw.textlength(right, font=small_font)) if right else 0
    name_width = max(120, x2 - cursor_x - right_width - 44)
    draw.text(
        (cursor_x, y1 + 17),
        _fit(draw, row.snapshot.display_name, name_font, name_width),
        font=name_font,
        fill=name_colour,
    )
    if right:
        draw.text((x2 - 20 - right_width, y1 + 25), right, font=small_font, fill=theme["muted"])

    context = _context(row, options)
    if context:
        draw.text((cursor_x, y1 + 55), context, font=meta_font, fill=theme["muted"])

    density = _opt(options, "leaderboard_density", "standard")
    bar_y = y1 + (82 if density != "compact" else 72)
    if _opt(options, "show_level_progress", True):
        bar_box = (x1 + 20, bar_y, x2 - 20, bar_y + 13)
        draw.rounded_rectangle(bar_box, radius=6, fill=theme["track"])
        ratio = max(0.0, min(1.0, row.snapshot.level / 60))
        if ratio:
            draw.rounded_rectangle(
                (bar_box[0], bar_box[1], bar_box[0] + int((bar_box[2] - bar_box[0]) * ratio), bar_box[3]),
                radius=6,
                fill=class_colour if _opt(options, "use_class_colours", True) else theme["progress"],
            )

    details_y = bar_y + 23
    professions = _profession_text(row, options)
    if professions:
        draw.text(
            (x1 + 20, details_y),
            _fit(draw, professions, small_font, x2 - x1 - 40),
            font=small_font,
            fill=theme["text"],
        )
        details_y += 25
    if density == "detailed":
        changes = _change_text(row, options)
        if changes:
            draw.text(
                (x1 + 20, details_y),
                _fit(draw, changes, small_font, x2 - x1 - 40),
                font=small_font,
                fill=theme["muted"],
            )


def render_leaderboard_png(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    options: Any,
    generated_at: Any,
) -> bytes:
    """Render factual leaderboard data into a deterministic PNG using Pillow only."""

    rows = list(progress)
    theme = THEMES.get(_opt(options, "image_theme", "dark_warcraft"), THEMES["dark_warcraft"])
    columns = 1 if _opt(options, "image_columns", "two") == "one" else 2
    if len(rows) < 2:
        columns = 1
    density = _opt(options, "leaderboard_density", "standard")
    row_height = {"compact": 112, "standard": 146, "detailed": 176}.get(density, 146)
    width = 1000 if columns == 1 else 1600
    margin = 44
    gutter = 24
    header_height = 154
    per_column = max(1, (len(rows) + columns - 1) // columns)
    height = header_height + margin + per_column * row_height + max(0, per_column - 1) * 14 + margin
    image = Image.new("RGB", (width, height), theme["background"])
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, header_height), fill=theme["header"])
    draw.rectangle((0, header_height - 5, width, header_height), fill=theme["gold"])
    title_font = _font(47, bold=True)
    sub_font = _font(20, bold=True)
    draw.text((margin, 30), "WOW FOREVER", font=title_font, fill=theme["text"])
    draw.text((margin, 91), "TRACKED-CHARACTER LEADERBOARD", font=sub_font, fill=theme["gold"])
    date_text = generated_at.strftime("%d %B %Y").upper()
    date_width = draw.textlength(date_text, font=sub_font)
    draw.text((width - margin - date_width, 91), date_text, font=sub_font, fill=theme["muted"])

    card_width = (width - 2 * margin - gutter * (columns - 1)) // columns
    for index, row in enumerate(rows):
        column = index // per_column
        row_index = index % per_column
        x1 = margin + column * (card_width + gutter)
        y1 = header_height + margin + row_index * (row_height + 14)
        _draw_card(
            draw,
            row,
            options,
            theme,
            (x1, y1, x1 + card_width, y1 + row_height),
            index,
        )

    output = BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()
