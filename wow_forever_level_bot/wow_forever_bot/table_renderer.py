from __future__ import annotations

from typing import Any, Iterable

from wcwidth import wcwidth, wcswidth

from .rendering import PROFESSION_SHORT, _opt
from .models import SnapshotProgress


def _width(text: str) -> int:
    value = wcswidth(text)
    return value if value >= 0 else len(text)


def _slice_visible(text: str, width: int) -> str:
    if width <= 0:
        return ""
    output: list[str] = []
    used = 0
    for character in text:
        character_width = wcwidth(character)
        if character_width < 0:
            character_width = 1
        if used + character_width > width:
            break
        output.append(character)
        used += character_width
    return "".join(output)


def _fit(text: str, width: int) -> str:
    if _width(text) <= width:
        return text
    if width <= 1:
        return _slice_visible(text, width)
    return _slice_visible(text, width - 1).rstrip() + "…"


def _pad(text: str, width: int, *, right: bool = False) -> str:
    text = _fit(text, width)
    padding = " " * max(0, width - _width(text))
    return padding + text if right else text + padding


def _wrap(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if _width(word) > width:
            if current:
                lines.append(current)
                current = ""
            remainder = word
            while _width(remainder) > width:
                part = _slice_visible(remainder, width)
                lines.append(part)
                remainder = remainder[len(part) :]
            current = remainder
            continue
        candidate = word if not current else current + " " + word
        if _width(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current or not lines:
        lines.append(current)
    return lines


def _movement(value: int | None) -> str:
    return "-" if not value else f"{value:+d}"


def _professions(row: SnapshotProgress, options: Any) -> str:
    if not _opt(options, "show_professions", False):
        return ""
    seen: set[str] = set()
    values: list[str] = []
    limit = 2
    for profession in row.snapshot.professions:
        key = profession.profession_name.casefold()
        if key in seen:
            continue
        seen.add(key)
        name = PROFESSION_SHORT.get(key, profession.profession_name[:2].upper())
        values.append(f"{name} {profession.skill_points:,}")
        if len(values) >= limit:
            break
    return ", ".join(values)


def _details(row: SnapshotProgress, options: Any) -> str:
    values: list[str] = []
    if _opt(options, "show_class", False) and row.snapshot.character_class:
        values.append(row.snapshot.character_class)
    if _opt(options, "show_race", False) and row.snapshot.race:
        values.append(row.snapshot.race)
    if _opt(options, "show_level_progress", False):
        values.append(f"Progress {round(row.snapshot.level / 60 * 100):d}%")
    professions = _professions(row, options)
    if professions:
        values.append(professions)
    if _opt(options, "show_notable_activity", False):
        if row.new_achievements_24h:
            first = row.new_achievements_24h[0]
            values.append(first.name or f"Achievement {first.achievement_id}")
        elif row.profession_skill_gains_24h:
            name, gain = row.profession_skill_gains_24h[0]
            values.append(f"{name} {gain:+d}")
    return " · ".join(values)


def _character(row: SnapshotProgress, options: Any) -> str:
    name = row.snapshot.display_name
    if _opt(options, "show_rank", True) and row.rank is not None:
        return f"{row.rank} {name}"
    return name


def _column_spec(rows: list[SnapshotProgress], options: Any) -> tuple[list[tuple[str, int, bool]], int]:
    target = 58
    character_cap = 23
    character_width = max(12, min(character_cap, max([9] + [_width(_character(row, options)) for row in rows])))

    columns: list[tuple[str, int, bool]] = [("Character", character_width, False)]
    if _opt(options, "show_level", True):
        columns.append(("Level", 5, True))
    if _opt(options, "show_24h_changes", True):
        columns.append(("24h", 3, True))
    if _opt(options, "show_7d_changes", False):
        columns.append(("7d", 3, True))
    if _opt(options, "show_lifetime_deaths", True):
        columns.append(("Deaths", 6, True))

    has_details = any(_details(row, options) for row in rows)
    if has_details:
        used = sum(width for _, width, _ in columns) + len(columns)
        details_width = target - used
        if details_width < 12:
            reduction = min(character_width - 12, 12 - details_width)
            character_width -= reduction
            columns[0] = ("Character", character_width, False)
            used = sum(width for _, width, _ in columns) + len(columns)
            details_width = target - used
        if details_width >= 10:
            columns.append(("Details", details_width, False))
        else:
            details_width = target - 2
    else:
        details_width = 0
    return columns, details_width


def _header(columns: list[tuple[str, int, bool]]) -> str:
    return " ".join(_pad(name, width, right=right) for name, width, right in columns).rstrip()


def _separator(columns: list[tuple[str, int, bool]]) -> str:
    return " ".join("-" * width for _, width, _ in columns).rstrip()


def _primary_values(row: SnapshotProgress, options: Any) -> list[str]:
    values = [_character(row, options)]
    if _opt(options, "show_level", True):
        values.append(str(row.snapshot.level))
    if _opt(options, "show_24h_changes", True):
        values.append(_movement(row.levels_24h))
    if _opt(options, "show_7d_changes", False):
        values.append(_movement(row.levels_7d))
    if _opt(options, "show_lifetime_deaths", True):
        deaths = row.snapshot.deaths.lifetime
        values.append("-" if deaths is None else f"{deaths:,}")
    return values


def leaderboard_table_lines(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    options: Any,
) -> list[str]:
    """Return a mobile-conscious Unicode-width-aware monospaced table."""

    rows = list(progress)
    if not rows:
        return ["No snapshot progress is available."]
    columns, details_width = _column_spec(rows, options)
    lines = [_header(columns), _separator(columns)]
    details_column = columns[-1][0] == "Details"

    for row in rows:
        values = _primary_values(row, options)
        details = _details(row, options)
        wrapped_details = _wrap(details, details_width) if details else [""]
        for line_index, details_line in enumerate(wrapped_details):
            cells: list[str] = []
            primary_columns = columns[:-1] if details_column else columns
            if line_index == 0:
                cells.extend(
                    _pad(value, width, right=right)
                    for value, (_, width, right) in zip(values, primary_columns)
                )
            else:
                cells.extend(" " * width for _, width, _ in primary_columns)
            if details_column:
                cells.append(_pad(details_line, columns[-1][1]))
                lines.append(" ".join(cells).rstrip())
            elif line_index == 0:
                lines.append(" ".join(cells).rstrip())
                if details:
                    for detail_line in _wrap(details, details_width):
                        lines.append("  " + detail_line)
    return lines


def leaderboard_table(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    options: Any,
) -> str:
    return "\n".join(leaderboard_table_lines(progress, options=options))


def leaderboard_table_code_blocks(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    options: Any,
    limit: int = 3900,
) -> list[str]:
    """Pack the table into safe Discord embed descriptions, repeating headers as needed."""

    lines = leaderboard_table_lines(progress, options=options)
    if len(lines) <= 2:
        return ["```text\n" + "\n".join(lines) + "\n```"]
    header = lines[:2]
    chunks: list[list[str]] = []
    current = header.copy()
    for line in lines[2:]:
        candidate = "```text\n" + "\n".join(current + [line]) + "\n```"
        if len(candidate) > limit and len(current) > len(header):
            chunks.append(current)
            current = header + [line]
        else:
            current.append(line)
    chunks.append(current)
    return ["```text\n" + "\n".join(chunk) + "\n```" for chunk in chunks]
