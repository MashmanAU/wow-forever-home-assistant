from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CharacterProfile:
    first_name: str
    surname: str
    region: str
    level: int

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.surname}"


@dataclass(frozen=True, slots=True)
class AchievementRecord:
    achievement_id: int
    name: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProfessionProgress:
    """One profession tier, identified by stable API IDs when available."""

    key: str
    profession_name: str
    tier_name: str | None
    skill_points: int
    max_skill_points: int | None = None

    @property
    def display_name(self) -> str:
        if self.tier_name and self.tier_name.casefold() != self.profession_name.casefold():
            return f"{self.profession_name} — {self.tier_name}"
        return self.profession_name


@dataclass(frozen=True, slots=True)
class DeathCounters:
    """Lifetime counters; daily values are derived from stored snapshots."""

    lifetime: int | None = None
    falling: int | None = None
    drowning: int | None = None
    fire_lava: int | None = None
    pvp: int | None = None
    dungeon_raid: int | None = None


@dataclass(frozen=True, slots=True)
class CharacterSnapshot:
    """Normalised facts collected from the WoW Forever Profile API.

    Raw Blizzard payloads are deliberately not stored. This controlled model is
    stable enough for deterministic deltas and is the only character dataset that
    future commentary code should receive.
    """

    first_name: str
    surname: str
    region: str
    captured_at: datetime
    level: int
    character_id: int | None = None
    experience: int | None = None
    average_item_level: float | None = None
    equipped_item_level: float | None = None
    last_login_at: datetime | None = None
    character_class: str | None = None
    race: str | None = None
    faction: str | None = None
    ruleset: str | None = None
    honorable_kills: int | None = None
    deaths: DeathCounters = field(default_factory=DeathCounters)
    achievements: tuple[AchievementRecord, ...] = ()
    professions: tuple[ProfessionProgress, ...] = ()
    source_errors: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.surname}"

    @property
    def profile(self) -> CharacterProfile:
        return CharacterProfile(self.first_name, self.surname, self.region, self.level)


@dataclass(frozen=True, slots=True)
class SnapshotProgress:
    """Derived, deterministic progress for one character at one point in time."""

    snapshot: CharacterSnapshot
    baseline_24h_at: datetime | None = None
    baseline_7d_at: datetime | None = None
    levels_24h: int | None = None
    levels_7d: int | None = None
    experience_24h: int | None = None
    deaths_24h: int | None = None
    falling_deaths_24h: int | None = None
    drowning_deaths_24h: int | None = None
    fire_lava_deaths_24h: int | None = None
    pvp_deaths_24h: int | None = None
    dungeon_raid_deaths_24h: int | None = None
    honorable_kills_24h: int | None = None
    average_item_level_change_24h: float | None = None
    equipped_item_level_change_24h: float | None = None
    new_achievements_24h: tuple[AchievementRecord, ...] = ()
    profession_skill_gains_24h: tuple[tuple[str, int], ...] = ()
    rank: int | None = None
    rank_change: int | None = None
    days_since_last_level: float | None = None


@dataclass(frozen=True, slots=True)
class CommentaryHistoryEntry:
    """Previously posted copy retained only to prevent repetitive commentary."""

    generated_at: datetime
    text: str
    source: str
    story_angle: str


@dataclass(frozen=True, slots=True)
class TrackedCharacter:
    guild_id: int
    first_name: str
    surname: str
    region: str
    level: int | None
    last_checked_at: datetime | None

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.surname}"


@dataclass(frozen=True, slots=True)
class RefreshResult:
    character: TrackedCharacter
    previous_level: int | None
    error: str | None = None

    @property
    def increase(self) -> int:
        if self.error or self.character.level is None or self.previous_level is None:
            return 0
        return max(0, self.character.level - self.previous_level)


@dataclass(frozen=True, slots=True)
class DailySchedule:
    guild_id: int
    channel_id: int
    time_of_day: str
    timezone: str
    next_run_utc: datetime
