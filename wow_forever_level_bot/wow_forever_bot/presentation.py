from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .daily import DailyBundle
from .models import SnapshotProgress

PROFESSION_EMOJIS = {
    "alchemy": "⚗️",
    "archaeology": "🏺",
    "blacksmithing": "⚒️",
    "cooking": "🍳",
    "enchanting": "✨",
    "engineering": "⚙️",
    "first aid": "🩹",
    "fishing": "🎣",
    "herbalism": "🌿",
    "inscription": "🖋️",
    "jewelcrafting": "💎",
    "leatherworking": "🪡",
    "mining": "⛏️",
    "skinning": "🔪",
    "tailoring": "🧵",
}

CLASS_COLOURS = {
    "death knight": 0xC41E3A,
    "demon hunter": 0xA330C9,
    "druid": 0xFF7C0A,
    "evoker": 0x33937F,
    "hunter": 0xAAD372,
    "mage": 0x3FC7EB,
    "monk": 0x00FF98,
    "paladin": 0xF48CBA,
    "priest": 0xFFFFFF,
    "rogue": 0xFFF468,
    "shaman": 0x0070DD,
    "warlock": 0x8788EE,
    "warrior": 0xC69B6D,
}

_DEFAULT_OPTIONS = SimpleNamespace(
    show_rank=True,
    show_race=True,
    show_class=True,
    show_level=True,
    show_level_progress=True,
    show_lifetime_deaths=True,
    show_professions=True,
    show_24h_changes=True,
    show_7d_changes=False,
    show_notable_activity=True,
    show_profession_icons=True,
)


def _option(options: Any | None, name: str, default: Any) -> Any:
    return getattr(options or _DEFAULT_OPTIONS, name, default)


def profession_icon(name: str) -> str:
    return PROFESSION_EMOJIS.get(name.casefold(), "🛠️")


def class_colour(name: str | None) -> int:
    return CLASS_COLOURS.get((name or "").casefold(), 0x5865F2)


def _signed(value: int | float, *, decimals: int = 0) -> str:
    if isinstance(value, float):
        text = f"{value:+.{decimals}f}".rstrip("0").rstrip(".")
        return "+0" if text in {"-0", "+0"} else text
    return f"{value:+,}"


def _progress_bar(level: int, *, width: int = 10) -> str:
    filled = max(0, min(width, round(level / 60 * width)))
    return "█" * filled + "░" * (width - filled)


def _identity_line(row: SnapshotProgress, options: Any, *, markdown: bool = True) -> str:
    snapshot = row.snapshot
    bold = (lambda value: f"**{value}**") if markdown else (lambda value: value)
    identity_parts: list[str] = []
    if _option(options, "show_rank", True) and row.rank is not None:
        movement = ""
        if row.rank_change:
            movement = f" {'↑' if row.rank_change > 0 else '↓'}{abs(row.rank_change)}"
        identity_parts.append(bold(f"#{row.rank} {snapshot.display_name}") + movement)
    else:
        identity_parts.append(bold(snapshot.display_name))

    context: list[str] = []
    if _option(options, "show_race", True) and snapshot.race:
        context.append(snapshot.race)
    if _option(options, "show_class", True) and snapshot.character_class:
        context.append(snapshot.character_class)
    if context:
        identity_parts.append(" ".join(context))
    if _option(options, "show_level", True):
        identity_parts.append(f"Lv {bold(str(snapshot.level))}")
    if _option(options, "show_level_progress", True):
        identity_parts.append(f"`{_progress_bar(snapshot.level)}`")
    return " · ".join(identity_parts)


def _profession_facts(row: SnapshotProgress, options: Any, *, limit: int) -> list[str]:
    seen: set[str] = set()
    facts: list[str] = []
    for profession in row.snapshot.professions:
        name = profession.profession_name
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        skill = f"{profession.skill_points:,}"
        if profession.max_skill_points is not None:
            skill += f"/{profession.max_skill_points:,}"
        icon = profession_icon(name) + " " if _option(options, "show_profession_icons", True) else ""
        facts.append(f"{icon}{name} **{skill}**")
        if len(facts) == limit:
            break
    remaining = len({p.profession_name.casefold() for p in row.snapshot.professions}) - len(facts)
    if remaining > 0:
        facts.append(f"+{remaining} profession{'s' if remaining != 1 else ''}")
    return facts


def _delta_facts(row: SnapshotProgress, options: Any, *, detailed: bool) -> list[str]:
    facts: list[str] = []
    if _option(options, "show_24h_changes", True):
        daily: list[str] = []
        if row.levels_24h:
            daily.append(f"Lv {_signed(row.levels_24h)}")
        if detailed and row.experience_24h and not row.levels_24h:
            daily.append(f"XP {_signed(row.experience_24h)}")
        if row.deaths_24h:
            daily.append(f"💀 {_signed(row.deaths_24h)}")
        if detailed and row.honorable_kills_24h:
            daily.append(f"HK {_signed(row.honorable_kills_24h)}")
        if detailed and row.average_item_level_change_24h:
            daily.append(f"iLvl {_signed(row.average_item_level_change_24h, decimals=1)}")
        if daily:
            facts.append("24h " + ", ".join(daily))
    if _option(options, "show_7d_changes", False) and row.levels_7d:
        facts.append(f"7d Lv {_signed(row.levels_7d)}")
    return facts


def _activity_facts(row: SnapshotProgress) -> list[str]:
    activity: list[str] = []
    if row.new_achievements_24h:
        first = row.new_achievements_24h[0]
        label = first.name or str(first.achievement_id)
        extra = len(row.new_achievements_24h) - 1
        activity.append(f"🏆 {label}" + (f" +{extra}" if extra else ""))
    if row.profession_skill_gains_24h:
        name, gain = row.profession_skill_gains_24h[0]
        activity.append(f"{profession_icon(name)} {name} {_signed(gain)}")
    return activity


def leaderboard_block(
    row: SnapshotProgress,
    *,
    options: Any | None = None,
) -> str:
    """Render one fixed-density native fallback character block."""

    options = options or _DEFAULT_OPTIONS
    first_line = _identity_line(row, options)
    second_line: list[str] = []

    if _option(options, "show_lifetime_deaths", True):
        lifetime = row.snapshot.deaths.lifetime
        second_line.append(f"💀 **{lifetime:,}**" if lifetime is not None else "💀 **n/a**")
    if _option(options, "show_professions", True):
        second_line.extend(_profession_facts(row, options, limit=2))
    second_line.extend(_delta_facts(row, options, detailed=False))

    if not second_line:
        return first_line
    return first_line + "\n↳ " + " · ".join(second_line)


def leaderboard_description(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    options: Any | None = None,
    limit: int = 4096,
) -> str:
    """Render every character inside one improved native Discord embed."""

    rows = list(progress)
    if not rows:
        return "No snapshot progress is available."
    options = options or _DEFAULT_OPTIONS
    description = "\n\n".join(leaderboard_block(row, options=options) for row in rows)
    if len(description) <= limit:
        return description

    # Last-resort native fallback retains every character and the two core facts.
    blocks = []
    for row in rows:
        rank = f"#{row.rank} " if row.rank is not None and _option(options, "show_rank", True) else ""
        level = f" · Lv {row.snapshot.level}" if _option(options, "show_level", True) else ""
        deaths = row.snapshot.deaths.lifetime
        death_text = (
            f" · 💀 {deaths:,}"
            if deaths is not None and _option(options, "show_lifetime_deaths", True)
            else ""
        )
        blocks.append(f"**{rank}{row.snapshot.display_name}**{level}{death_text}")
    description = "\n".join(blocks)
    if len(description) > limit:
        raise ValueError("The tracked roster is too large for one Discord leaderboard embed")
    return description


def daily_message_content(
    bundle: DailyBundle,
    *,
    mention_everyone: bool = False,
    notice: str | None = None,
) -> str:
    parts: list[str] = []
    if mention_everyone:
        parts.append("@everyone")
    if notice:
        parts.append(notice)
    parts.extend(("📻 **WoW Forever daily**", bundle.commentary.text))
    return "\n\n".join(parts)
