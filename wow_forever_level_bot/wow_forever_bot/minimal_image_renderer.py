from __future__ import annotations

from io import BytesIO
from math import cos, pi, sin
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .image_renderer import THEMES, _fit, _font, _opt, _profession_text
from .models import SnapshotProgress
from .presentation import CLASS_COLOURS


def _class_colour(name: str | None) -> str:
    return f"#{CLASS_COLOURS.get((name or '').casefold(), 0x5865F2):06x}"


def _line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], *, fill: str, width: int = 4) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")


def _draw_class_glyph(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    class_name: str | None,
    colour: str,
) -> None:
    """Draw a deterministic, dependency-free class glyph inside a large square badge."""

    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=10, fill="#111318", outline=colour, width=3)
    name = (class_name or "").casefold()
    ink = colour
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    w, h = x2 - x1, y2 - y1

    if name in {"warrior", "rogue"}:
        _line(draw, [(x1 + 12, y2 - 10), (x2 - 11, y1 + 9)], fill=ink, width=5)
        _line(draw, [(x1 + 11, y1 + 10), (x2 - 12, y2 - 9)], fill=ink, width=5)
        draw.polygon([(x2 - 8, y1 + 6), (x2 - 14, y1 + 20), (x2 - 21, y1 + 13)], fill=ink)
        draw.polygon([(x2 - 8, y2 - 6), (x2 - 21, y2 - 13), (x2 - 14, y2 - 20)], fill=ink)
    elif name == "hunter":
        draw.arc((x1 + 8, y1 + 7, x2 - 8, y2 - 7), 85, 275, fill=ink, width=5)
        _line(draw, [(x1 + 14, cy), (x2 - 10, cy)], fill=ink, width=4)
        draw.polygon([(x2 - 7, cy), (x2 - 18, cy - 6), (x2 - 18, cy + 6)], fill=ink)
    elif name in {"paladin", "priest"}:
        draw.rounded_rectangle((cx - 4, y1 + 8, cx + 4, y2 - 8), radius=3, fill=ink)
        draw.rounded_rectangle((x1 + 10, cy - 4, x2 - 10, cy + 4), radius=3, fill=ink)
        if name == "paladin":
            draw.ellipse((x1 + 8, y1 + 8, x2 - 8, y2 - 8), outline=ink, width=3)
    elif name == "shaman":
        draw.polygon(
            [
                (cx + 3, y1 + 6),
                (x1 + 13, cy + 2),
                (cx - 1, cy + 2),
                (cx - 5, y2 - 6),
                (x2 - 11, cy - 5),
                (cx + 2, cy - 5),
            ],
            fill=ink,
        )
    elif name == "mage":
        for angle in (0, pi / 3, 2 * pi / 3):
            dx, dy = cos(angle) * w * 0.32, sin(angle) * h * 0.32
            _line(draw, [(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=ink, width=4)
        draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=ink)
    elif name == "druid":
        draw.ellipse((cx - 7, cy - 2, cx + 7, cy + 12), fill=ink)
        for ox, oy in ((-14, -9), (-5, -15), (5, -15), (14, -9)):
            draw.ellipse((cx + ox - 4, cy + oy - 4, cx + ox + 4, cy + oy + 4), fill=ink)
    elif name in {"warlock", "demon hunter"}:
        draw.arc((x1 + 8, y1 + 8, x2 - 8, y2 - 8), 20, 330, fill=ink, width=5)
        draw.arc((x1 + 16, y1 + 16, x2 - 16, y2 - 16), 200, 520, fill=ink, width=4)
    elif name == "death knight":
        draw.polygon([(cx, y1 + 7), (x2 - 9, cy), (cx, y2 - 7), (x1 + 9, cy)], outline=ink)
        _line(draw, [(cx, y1 + 11), (cx, y2 - 11)], fill=ink, width=4)
        _line(draw, [(x1 + 14, cy), (x2 - 14, cy)], fill=ink, width=4)
    elif name == "monk":
        draw.ellipse((x1 + 9, y1 + 9, x2 - 9, y2 - 9), outline=ink, width=4)
        draw.arc((x1 + 14, y1 + 10, x2 - 14, y2 - 10), 90, 270, fill=ink, width=4)
        draw.ellipse((cx - 4, y1 + 16, cx + 4, y1 + 24), fill=ink)
        draw.ellipse((cx - 4, y2 - 24, cx + 4, y2 - 16), fill=ink)
    elif name == "evoker":
        draw.polygon([(cx, y1 + 7), (x2 - 7, cy), (cx + 5, cy - 2), (cx, y2 - 7), (cx - 5, cy - 2), (x1 + 7, cy)], fill=ink)
    else:
        initials = "".join(word[:1] for word in (class_name or "?").split())[:2].upper() or "?"
        font = _font(20, bold=True)
        bbox = draw.textbbox((0, 0), initials, font=font)
        draw.text((cx - (bbox[2] - bbox[0]) / 2, cy - (bbox[3] - bbox[1]) / 2 - 2), initials, font=font, fill=ink)


def _movement(value: int | None) -> str:
    if not value:
        return "-"
    return f"{value:+d}"


def _secondary_text(row: SnapshotProgress, options: Any) -> str:
    values: list[str] = []
    if _opt(options, "show_race", False) and row.snapshot.race:
        values.append(row.snapshot.race)
    if _opt(options, "show_class", False) and row.snapshot.character_class:
        values.append(row.snapshot.character_class)
    if _opt(options, "show_7d_changes", False):
        values.append(f"7d {_movement(row.levels_7d)}")
    professions = _profession_text(row, options)
    if professions:
        values.append(professions)
    if _opt(options, "show_notable_activity", False) and row.new_achievements_24h:
        achievement = row.new_achievements_24h[0]
        values.append(achievement.name or f"Achievement {achievement.achievement_id}")
    return "  •  ".join(values)


def render_minimal_leaderboard_png(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    options: Any,
    generated_at: Any,
) -> bytes:
    """Render a narrow, large-type, single-column leaderboard for Discord inline use."""

    rows = list(progress)
    theme_name = _opt(options, "image_theme", "dark_warcraft")
    theme = THEMES.get(theme_name, THEMES["dark_warcraft"])
    secondary_enabled = bool(
        _opt(options, "show_race", False)
        or _opt(options, "show_class", False)
        or _opt(options, "show_professions", False)
        or _opt(options, "show_7d_changes", False)
        or _opt(options, "show_notable_activity", False)
        or _opt(options, "show_level_progress", False)
    )
    # Keep the source PNG narrow and make the name the dominant element. The
    # default row stays on one line; secondary fields still expand only when a
    # user explicitly enables them.
    width = 540
    outer_padding = 4
    row_height = 72 if secondary_enabled else 54
    height = outer_padding * 2 + len(rows) * row_height

    image = Image.new("RGB", (width, height), theme["background"])
    draw = ImageDraw.Draw(image)

    name_font = _font(27, bold=True, condensed=True)
    badge_font = _font(19, bold=True, condensed=True)
    movement_font = _font(18, bold=True, condensed=True)
    death_font = _font(15, bold=True, condensed=True)
    small_font = _font(13, condensed=True)
    rank_font = _font(10, bold=True, condensed=True)

    for index, row in enumerate(rows):
        y1 = outer_padding + index * row_height
        y2 = y1 + row_height
        # Flat bands replace the padded rounded cards from v1.9.0.
        fill = theme["card_alt"] if index % 2 else theme["card"]
        draw.rectangle((0, y1, width, y2), fill=fill)
        if index:
            draw.line((0, y1, width, y1), fill=theme["background"], width=1)
        x = 6
        primary_centre_y = y1 + 27
        class_name = row.snapshot.character_class
        colour = _class_colour(class_name) if _opt(options, "use_class_colours", True) else theme["text"]

        if _opt(options, "show_class_icons", True):
            icon_box = (x, y1 + 3, x + 48, y1 + 51)
            _draw_class_glyph(draw, icon_box, class_name, colour)
            if _opt(options, "show_rank", False) and row.rank is not None:
                rank_text = str(row.rank)
                rank_box = (x + 30, y1 + 33, x + 48, y1 + 51)
                draw.ellipse(rank_box, fill=theme["gold"])
                draw.text(
                    ((rank_box[0] + rank_box[2]) / 2, (rank_box[1] + rank_box[3]) / 2),
                    rank_text,
                    font=rank_font,
                    fill="#17130b",
                    anchor="mm",
                )
            x += 54
        elif _opt(options, "show_rank", False) and row.rank is not None:
            rank_text = f"{row.rank}."
            draw.text((x, primary_centre_y), rank_text, font=small_font, fill=theme["muted"], anchor="lm")
            x += int(draw.textlength(rank_text, font=small_font)) + 8

        if _opt(options, "show_level", True):
            badge_width = 46
            draw.rounded_rectangle((x, y1 + 4, x + badge_width, y1 + 50), radius=7, fill=theme["border"])
            level_text = str(row.snapshot.level)
            draw.text(
                (x + badge_width / 2, primary_centre_y),
                level_text,
                font=badge_font,
                fill=theme["text"],
                anchor="mm",
            )
            x += badge_width + 4

        if _opt(options, "show_24h_changes", True):
            move_text = _movement(row.levels_24h)
            move_colour = "#65d48a" if (row.levels_24h or 0) > 0 else theme["muted"]
            move_width = max(22, int(draw.textlength(move_text, font=movement_font)))
            draw.text((x, primary_centre_y), move_text, font=movement_font, fill=move_colour, anchor="lm")
            x += move_width + 6

        death_text = ""
        if _opt(options, "show_lifetime_deaths", True):
            deaths = row.snapshot.deaths.lifetime
            death_text = f"☠ {deaths:,}" if deaths is not None else "☠ -"
        death_width = int(draw.textlength(death_text, font=death_font)) if death_text else 0
        right_edge = width - 8
        if death_text:
            draw.text((right_edge, primary_centre_y), death_text, font=death_font, fill=theme["muted"], anchor="rm")

        name_width = max(60, right_edge - death_width - 8 - x)
        name_colour = colour if _opt(options, "use_class_colours", True) else theme["text"]
        draw.text(
            (x, primary_centre_y),
            _fit(draw, row.snapshot.display_name.upper(), name_font, name_width),
            font=name_font,
            fill=name_colour,
            anchor="lm",
        )

        if secondary_enabled:
            secondary = _secondary_text(row, options)
            if secondary:
                draw.text(
                    (x, y1 + 54),
                    _fit(draw, secondary, small_font, right_edge - x),
                    font=small_font,
                    fill=theme["muted"],
                    anchor="lm",
                )
            if _opt(options, "show_level_progress", False):
                bar_y = y2 - 5
                draw.rounded_rectangle((x, bar_y, right_edge, bar_y + 3), radius=2, fill=theme["track"])
                ratio = max(0.0, min(1.0, row.snapshot.level / 60))
                if ratio:
                    draw.rounded_rectangle(
                        (x, bar_y, x + int((right_edge - x) * ratio), bar_y + 3),
                        radius=2,
                        fill=colour,
                    )

    output = BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()
