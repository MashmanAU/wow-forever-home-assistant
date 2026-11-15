from __future__ import annotations

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


def profession_icon(name: str) -> str:
    return PROFESSION_EMOJIS.get(name.casefold(), "🛠️")


def _signed(value: int | float, *, decimals: int = 0) -> str:
    if isinstance(value, float):
        text = f"{value:+.{decimals}f}".rstrip("0").rstrip(".")
        return "+0" if text in {"-0", "+0"} else text
    return f"{value:+,}"


def _identity_line(row: SnapshotProgress, *, minimal: bool = False) -> str:
    snapshot = row.snapshot
    if row.rank is not None:
        movement = ""
        if row.rank_change:
            movement = f" {'↑' if row.rank_change > 0 else '↓'}{abs(row.rank_change)}"
        identity = f"**#{row.rank} {snapshot.display_name}**{movement}"
    else:
        identity = f"**{snapshot.display_name}**"

    if not minimal:
        context = [item for item in (snapshot.race, snapshot.character_class) if item]
        if context:
            identity += " · " + " ".join(context)
    return f"{identity} · Lv **{snapshot.level}/60**"


def _profession_facts(row: SnapshotProgress, *, limit: int) -> list[str]:
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
        facts.append(f"{profession_icon(name)} {name} **{skill}**")
        if len(facts) == limit:
            break
    remaining = len(
        {
            profession.profession_name.casefold()
            for profession in row.snapshot.professions
        }
    ) - len(facts)
    if remaining > 0:
        facts.append(f"+{remaining} profession{'s' if remaining != 1 else ''}")
    return facts


def _delta_facts(row: SnapshotProgress, *, extended: bool) -> list[str]:
    facts: list[str] = []
    daily: list[str] = []
    if row.levels_24h is not None:
        daily.append(f"Lv {_signed(row.levels_24h)}")
    if (
        extended
        and row.experience_24h is not None
        and row.experience_24h > 0
        and not row.levels_24h
    ):
        daily.append(f"XP {_signed(row.experience_24h)}")
    if row.deaths_24h:
        daily.append(f"💀 {_signed(row.deaths_24h)}")
    if extended and row.honorable_kills_24h:
        daily.append(f"HK {_signed(row.honorable_kills_24h)}")
    if extended and row.average_item_level_change_24h:
        daily.append(f"iLvl {_signed(row.average_item_level_change_24h, decimals=1)}")
    if daily:
        facts.append("24h " + ", ".join(daily))
    if row.levels_7d is not None:
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


def leaderboard_block(row: SnapshotProgress, *, density: str = "full") -> str:
    """Return exactly two Discord Markdown lines for one character."""

    minimal = density == "minimal"
    first_line = _identity_line(row, minimal=minimal)
    lifetime = row.snapshot.deaths.lifetime
    second_line = [f"💀 **{lifetime:,}**" if lifetime is not None else "💀 **n/a**"]

    if density == "full":
        second_line.extend(_profession_facts(row, limit=2))
        second_line.extend(_delta_facts(row, extended=True))
        second_line.extend(_activity_facts(row))
    elif density == "condensed":
        second_line.extend(_profession_facts(row, limit=1))
        second_line.extend(_delta_facts(row, extended=False))
    else:
        second_line.extend(_delta_facts(row, extended=False))

    return first_line + "\n↳ " + " · ".join(second_line)


def leaderboard_description(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    limit: int = 4096,
) -> str:
    """Render every character inside one Discord embed description."""

    rows = list(progress)
    if not rows:
        return "No snapshot progress is available."

    for density in ("full", "condensed", "minimal"):
        description = "\n".join(leaderboard_block(row, density=density) for row in rows)
        if len(description) <= limit:
            return description

    # Extremely large rosters still retain every name, level and death counter in
    # one embed. Discord names and Blizzard levels are bounded, so this is the
    # final deterministic safety reduction rather than creating another embed.
    blocks = [
        f"**{row.snapshot.display_name}** · Lv **{row.snapshot.level}/60**\n"
        f"↳ 💀 **{row.snapshot.deaths.lifetime:,}**"
        if row.snapshot.deaths.lifetime is not None
        else f"**{row.snapshot.display_name}** · Lv **{row.snapshot.level}/60**\n↳ 💀 **n/a**"
        for row in rows
    ]
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
