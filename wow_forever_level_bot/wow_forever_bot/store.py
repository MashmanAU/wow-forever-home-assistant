from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .models import (
    AchievementRecord,
    CharacterProfile,
    CharacterSnapshot,
    CommentaryHistoryEntry,
    DailySchedule,
    DeathCounters,
    ProfessionProgress,
    SnapshotProgress,
    TrackedCharacter,
)

CHARACTER_COLUMNS = {
    "guild_id",
    "first_name",
    "surname",
    "region",
    "level",
    "last_checked_at",
    "added_by",
    "created_at",
}
SCHEDULE_COLUMNS = {
    "guild_id",
    "channel_id",
    "time_of_day",
    "timezone",
    "next_run_utc",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pick(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def _json_list(value: Any) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []


def _monotonic_delta(current: int | None, previous: int | None) -> int | None:
    if current is None or previous is None or current < previous:
        return None
    return current - previous


def _float_delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 3)


class Store:
    def __init__(self, path: str, default_timezone: str = "Australia/Sydney") -> None:
        self.path = Path(path)
        self.default_timezone = default_timezone
        self._lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with self._lock:
            await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        with self._connect() as db:
            self._migrate_characters(db)
            self._migrate_schedules(db)
            self._create_snapshots(db)
            self._create_commentary_history(db)
            db.execute("PRAGMA user_version = 150")

    @staticmethod
    def _create_snapshots(db: sqlite3.Connection) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                first_name TEXT NOT NULL,
                surname TEXT NOT NULL,
                region TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                character_id INTEGER,
                level INTEGER NOT NULL,
                experience INTEGER,
                average_item_level REAL,
                equipped_item_level REAL,
                last_login_at TEXT,
                character_class TEXT,
                race TEXT,
                faction TEXT,
                ruleset TEXT,
                honorable_kills INTEGER,
                lifetime_deaths INTEGER,
                falling_deaths INTEGER,
                drowning_deaths INTEGER,
                fire_lava_deaths INTEGER,
                pvp_deaths INTEGER,
                dungeon_raid_deaths INTEGER,
                achievements_json TEXT NOT NULL,
                professions_json TEXT NOT NULL,
                source_errors_json TEXT NOT NULL,
                UNIQUE (guild_id, first_name, surname, region, captured_at)
            )
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_character_snapshots_lookup
            ON character_snapshots
            (guild_id, first_name, surname, region, captured_at DESC)
            """
        )

    @staticmethod
    def _create_commentary_history(db: sqlite3.Connection) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS commentary_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                story_angle TEXT NOT NULL,
                UNIQUE (guild_id, generated_at)
            )
            """
        )
        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_commentary_history_recent
            ON commentary_history (guild_id, generated_at DESC)
            """
        )

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return (
            db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
            ).fetchone()
            is not None
        )

    @staticmethod
    def _columns(db: sqlite3.Connection, name: str) -> set[str]:
        return {str(row["name"]) for row in db.execute(f'PRAGMA table_info("{name}")')}

    @staticmethod
    def _create_characters(db: sqlite3.Connection) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS characters (
                guild_id INTEGER NOT NULL,
                first_name TEXT NOT NULL,
                surname TEXT NOT NULL,
                region TEXT NOT NULL,
                level INTEGER,
                last_checked_at TEXT,
                added_by INTEGER,
                created_at TEXT NOT NULL,
                PRIMARY KEY (guild_id, first_name, surname, region)
            )
            """
        )

    def _migrate_characters(self, db: sqlite3.Connection) -> None:
        sources: list[str] = []
        if self._table_exists(db, "characters"):
            if CHARACTER_COLUMNS.issubset(self._columns(db, "characters")):
                return
            sources.append("characters")
        if self._table_exists(db, "tracked_characters"):
            sources.append("tracked_characters")

        rows: list[dict[str, Any]] = []
        for source in sources:
            rows.extend(dict(row) for row in db.execute(f'SELECT * FROM "{source}"'))
            db.execute(f'DROP TABLE "{source}"')
        self._create_characters(db)

        now = _iso(_utcnow())
        for row in rows:
            guild_id = _pick(row, "guild_id", "server_id")
            first_name = _pick(row, "first_name", "firstname", "name")
            surname = _pick(row, "surname", "last_name", "lastname")
            if guild_id is None or not first_name or not surname:
                continue
            db.execute(
                """
                INSERT OR REPLACE INTO characters
                (guild_id, first_name, surname, region, level, last_checked_at, added_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(guild_id),
                    str(first_name),
                    str(surname),
                    str(_pick(row, "region", default="us")).lower(),
                    _pick(row, "level", "last_level", "cached_level"),
                    _pick(row, "last_checked_at", "last_checked", "updated_at"),
                    _pick(row, "added_by", "added_by_user_id"),
                    _pick(row, "created_at", "added_at", default=now),
                ),
            )

    @staticmethod
    def _create_schedules(db: sqlite3.Connection) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                time_of_day TEXT NOT NULL,
                timezone TEXT NOT NULL,
                next_run_utc TEXT NOT NULL
            )
            """
        )

    def _migrate_schedules(self, db: sqlite3.Connection) -> None:
        if not self._table_exists(db, "schedules"):
            self._create_schedules(db)
            return
        if SCHEDULE_COLUMNS.issubset(self._columns(db, "schedules")):
            return

        rows = [dict(row) for row in db.execute("SELECT * FROM schedules")]
        db.execute("DROP TABLE schedules")
        self._create_schedules(db)
        try:
            zone = ZoneInfo(self.default_timezone)
        except Exception:
            zone = ZoneInfo("UTC")

        for row in rows:
            guild_id = _pick(row, "guild_id", "server_id")
            channel_id = _pick(row, "channel_id")
            if guild_id is None or channel_id is None:
                continue
            next_run = _parse_datetime(
                _pick(row, "next_run_utc", "next_run_at", "next_run", "run_at")
            )
            if next_run is None:
                next_run = _utcnow()
            timezone_name = str(_pick(row, "timezone", "timezone_name", default=self.default_timezone))
            time_of_day = _pick(row, "time_of_day", "daily_time")
            if not time_of_day:
                time_of_day = next_run.astimezone(zone).strftime("%H:%M")
            db.execute(
                """
                INSERT OR REPLACE INTO schedules
                (guild_id, channel_id, time_of_day, timezone, next_run_utc)
                VALUES (?, ?, ?, ?, ?)
                """,
                (int(guild_id), int(channel_id), str(time_of_day), timezone_name, _iso(next_run)),
            )

    async def add_character(
        self, guild_id: int, profile: CharacterProfile, added_by: int
    ) -> bool:
        async with self._lock:
            return await asyncio.to_thread(
                self._add_character_sync, guild_id, profile, added_by
            )

    def _add_character_sync(
        self, guild_id: int, profile: CharacterProfile, added_by: int
    ) -> bool:
        now = _iso(_utcnow())
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO characters
                (guild_id, first_name, surname, region, level, last_checked_at, added_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    profile.first_name,
                    profile.surname,
                    profile.region,
                    profile.level,
                    now,
                    added_by,
                    now,
                ),
            )
            return cursor.rowcount == 1

    async def remove_character(
        self, guild_id: int, first_name: str, surname: str, region: str
    ) -> bool:
        async with self._lock:
            return await asyncio.to_thread(
                self._remove_character_sync, guild_id, first_name, surname, region
            )

    def _remove_character_sync(
        self, guild_id: int, first_name: str, surname: str, region: str
    ) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                """
                DELETE FROM characters
                WHERE guild_id=? AND lower(first_name)=lower(?)
                  AND lower(surname)=lower(?) AND region=?
                """,
                (guild_id, first_name.strip(), surname.strip(), region.lower()),
            )
            if cursor.rowcount == 1:
                db.execute(
                    """
                    DELETE FROM character_snapshots
                    WHERE guild_id=? AND lower(first_name)=lower(?)
                      AND lower(surname)=lower(?) AND region=?
                    """,
                    (guild_id, first_name.strip(), surname.strip(), region.lower()),
                )
            return cursor.rowcount == 1

    async def list_characters(self, guild_id: int) -> list[TrackedCharacter]:
        async with self._lock:
            rows = await asyncio.to_thread(self._list_characters_sync, guild_id)
        return [self._tracked_from_row(row) for row in rows]

    def _list_characters_sync(self, guild_id: int) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    """
                    SELECT guild_id, first_name, surname, region, level, last_checked_at
                    FROM characters WHERE guild_id=?
                    """,
                    (guild_id,),
                )
            ]

    @staticmethod
    def _tracked_from_row(row: dict[str, Any]) -> TrackedCharacter:
        return TrackedCharacter(
            guild_id=int(row["guild_id"]),
            first_name=str(row["first_name"]),
            surname=str(row["surname"]),
            region=str(row["region"]),
            level=int(row["level"]) if row["level"] is not None else None,
            last_checked_at=_parse_datetime(row.get("last_checked_at")),
        )

    async def update_character(self, guild_id: int, profile: CharacterProfile) -> None:
        async with self._lock:
            await asyncio.to_thread(self._update_character_sync, guild_id, profile)

    def _update_character_sync(self, guild_id: int, profile: CharacterProfile) -> None:
        with self._connect() as db:
            db.execute(
                """
                UPDATE characters SET level=?, last_checked_at=?
                WHERE guild_id=? AND lower(first_name)=lower(?)
                  AND lower(surname)=lower(?) AND region=?
                """,
                (
                    profile.level,
                    _iso(_utcnow()),
                    guild_id,
                    profile.first_name,
                    profile.surname,
                    profile.region,
                ),
            )

    async def save_snapshot(self, guild_id: int, snapshot: CharacterSnapshot) -> bool:
        """Persist one normalised snapshot; identical timestamp retries are idempotent."""

        async with self._lock:
            return await asyncio.to_thread(self._save_snapshot_sync, guild_id, snapshot)

    def _save_snapshot_sync(self, guild_id: int, snapshot: CharacterSnapshot) -> bool:
        achievements = [
            {
                "achievement_id": item.achievement_id,
                "name": item.name,
                "completed_at": _iso(item.completed_at) if item.completed_at else None,
            }
            for item in snapshot.achievements
        ]
        professions = [
            {
                "key": item.key,
                "profession_name": item.profession_name,
                "tier_name": item.tier_name,
                "skill_points": item.skill_points,
                "max_skill_points": item.max_skill_points,
            }
            for item in snapshot.professions
        ]
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT OR IGNORE INTO character_snapshots (
                    guild_id, first_name, surname, region, captured_at,
                    character_id, level, experience, average_item_level,
                    equipped_item_level, last_login_at, character_class, race,
                    faction, ruleset, honorable_kills, lifetime_deaths,
                    falling_deaths, drowning_deaths, fire_lava_deaths,
                    pvp_deaths, dungeon_raid_deaths, achievements_json,
                    professions_json, source_errors_json
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    guild_id,
                    snapshot.first_name,
                    snapshot.surname,
                    snapshot.region,
                    _iso(snapshot.captured_at),
                    snapshot.character_id,
                    snapshot.level,
                    snapshot.experience,
                    snapshot.average_item_level,
                    snapshot.equipped_item_level,
                    _iso(snapshot.last_login_at) if snapshot.last_login_at else None,
                    snapshot.character_class,
                    snapshot.race,
                    snapshot.faction,
                    snapshot.ruleset,
                    snapshot.honorable_kills,
                    snapshot.deaths.lifetime,
                    snapshot.deaths.falling,
                    snapshot.deaths.drowning,
                    snapshot.deaths.fire_lava,
                    snapshot.deaths.pvp,
                    snapshot.deaths.dungeon_raid,
                    json.dumps(achievements, ensure_ascii=False, sort_keys=True),
                    json.dumps(professions, ensure_ascii=False, sort_keys=True),
                    json.dumps(list(snapshot.source_errors), ensure_ascii=False),
                ),
            )
            return cursor.rowcount == 1

    @staticmethod
    def _snapshot_from_row(row: dict[str, Any]) -> CharacterSnapshot:
        captured_at = _parse_datetime(row.get("captured_at"))
        assert captured_at is not None
        achievements: list[AchievementRecord] = []
        for item in _json_list(row.get("achievements_json")):
            achievement_id = item.get("achievement_id")
            if isinstance(achievement_id, bool) or not isinstance(achievement_id, int):
                continue
            achievements.append(
                AchievementRecord(
                    achievement_id=achievement_id,
                    name=str(item["name"]) if item.get("name") is not None else None,
                    completed_at=_parse_datetime(item.get("completed_at")),
                )
            )
        professions: list[ProfessionProgress] = []
        for item in _json_list(row.get("professions_json")):
            try:
                professions.append(
                    ProfessionProgress(
                        key=str(item["key"]),
                        profession_name=str(item["profession_name"]),
                        tier_name=str(item["tier_name"]) if item.get("tier_name") else None,
                        skill_points=int(item["skill_points"]),
                        max_skill_points=(
                            int(item["max_skill_points"])
                            if item.get("max_skill_points") is not None
                            else None
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        try:
            errors_value = json.loads(str(row.get("source_errors_json") or "[]"))
            source_errors = tuple(str(item) for item in errors_value) if isinstance(errors_value, list) else ()
        except (TypeError, ValueError, json.JSONDecodeError):
            source_errors = ()
        return CharacterSnapshot(
            first_name=str(row["first_name"]),
            surname=str(row["surname"]),
            region=str(row["region"]),
            captured_at=captured_at,
            level=int(row["level"]),
            character_id=int(row["character_id"]) if row.get("character_id") is not None else None,
            experience=int(row["experience"]) if row.get("experience") is not None else None,
            average_item_level=(
                float(row["average_item_level"])
                if row.get("average_item_level") is not None
                else None
            ),
            equipped_item_level=(
                float(row["equipped_item_level"])
                if row.get("equipped_item_level") is not None
                else None
            ),
            last_login_at=_parse_datetime(row.get("last_login_at")),
            character_class=str(row["character_class"]) if row.get("character_class") else None,
            race=str(row["race"]) if row.get("race") else None,
            faction=str(row["faction"]) if row.get("faction") else None,
            ruleset=str(row["ruleset"]) if row.get("ruleset") else None,
            honorable_kills=(
                int(row["honorable_kills"])
                if row.get("honorable_kills") is not None
                else None
            ),
            deaths=DeathCounters(
                lifetime=int(row["lifetime_deaths"]) if row.get("lifetime_deaths") is not None else None,
                falling=int(row["falling_deaths"]) if row.get("falling_deaths") is not None else None,
                drowning=int(row["drowning_deaths"]) if row.get("drowning_deaths") is not None else None,
                fire_lava=int(row["fire_lava_deaths"]) if row.get("fire_lava_deaths") is not None else None,
                pvp=int(row["pvp_deaths"]) if row.get("pvp_deaths") is not None else None,
                dungeon_raid=(
                    int(row["dungeon_raid_deaths"])
                    if row.get("dungeon_raid_deaths") is not None
                    else None
                ),
            ),
            achievements=tuple(sorted(achievements, key=lambda item: item.achievement_id)),
            professions=tuple(sorted(professions, key=lambda item: item.key)),
            source_errors=source_errors,
        )

    async def list_snapshots(
        self,
        guild_id: int,
        first_name: str | None = None,
        surname: str | None = None,
        region: str | None = None,
        since: datetime | None = None,
    ) -> list[CharacterSnapshot]:
        async with self._lock:
            rows = await asyncio.to_thread(
                self._list_snapshots_sync,
                guild_id,
                first_name,
                surname,
                region,
                since,
            )
        return [self._snapshot_from_row(row) for row in rows]

    def _list_snapshots_sync(
        self,
        guild_id: int,
        first_name: str | None,
        surname: str | None,
        region: str | None,
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        clauses = ["guild_id=?"]
        values: list[Any] = [guild_id]
        if first_name is not None:
            clauses.append("lower(first_name)=lower(?)")
            values.append(first_name.strip())
        if surname is not None:
            clauses.append("lower(surname)=lower(?)")
            values.append(surname.strip())
        if region is not None:
            clauses.append("region=?")
            values.append(region.casefold().strip())
        if since is not None:
            clauses.append("captured_at>=?")
            values.append(_iso(since))
        query = (
            "SELECT * FROM character_snapshots WHERE "
            + " AND ".join(clauses)
            + " ORDER BY captured_at ASC, id ASC"
        )
        with self._connect() as db:
            return [dict(row) for row in db.execute(query, values)]

    async def snapshot_progress(
        self, guild_id: int, as_of: datetime | None = None
    ) -> list[SnapshotProgress]:
        """Calculate controlled 24-hour/7-day deltas and leaderboard movement."""

        snapshots = await self.list_snapshots(guild_id)
        return self._derive_progress(snapshots, as_of)

    async def preview_progress_with_current(
        self,
        guild_id: int,
        current_snapshots: Iterable[CharacterSnapshot],
        as_of: datetime | None = None,
    ) -> list[SnapshotProgress]:
        """Derive progress against ephemeral live snapshots without persisting them.

        This read-only path intentionally reuses the production delta algorithm while
        keeping the supplied current snapshots in memory. It never calls a Store
        insert/update method, so the persisted 24-hour and 7-day history is unchanged.
        """

        history = await self.list_snapshots(guild_id)
        combined = [*history, *current_snapshots]
        return self._derive_progress(combined, as_of)

    @staticmethod
    def _derive_progress(
        snapshots: list[CharacterSnapshot], as_of: datetime | None = None
    ) -> list[SnapshotProgress]:
        cutoff = (as_of or _utcnow()).astimezone(timezone.utc)
        grouped: dict[tuple[str, str, str], list[CharacterSnapshot]] = {}
        for snapshot in snapshots:
            if snapshot.captured_at > cutoff:
                continue
            key = (
                snapshot.first_name.casefold(),
                snapshot.surname.casefold(),
                snapshot.region.casefold(),
            )
            grouped.setdefault(key, []).append(snapshot)
        for history in grouped.values():
            history.sort(key=lambda item: item.captured_at)

        current = {key: history[-1] for key, history in grouped.items() if history}
        ordered_keys = sorted(
            current,
            key=lambda key: (
                -current[key].level,
                -(current[key].experience if current[key].experience is not None else -1),
                current[key].display_name.casefold(),
            ),
        )
        ranks = {key: index + 1 for index, key in enumerate(ordered_keys)}

        baseline_24: dict[tuple[str, str, str], CharacterSnapshot] = {}
        baseline_7d: dict[tuple[str, str, str], CharacterSnapshot] = {}
        for key, latest in current.items():
            history = grouped[key]
            target_24 = latest.captured_at - timedelta(hours=24)
            minimum_24 = latest.captured_at - timedelta(hours=48)
            choices_24 = [item for item in history if minimum_24 <= item.captured_at <= target_24]
            if choices_24:
                baseline_24[key] = choices_24[-1]
            target_7d = latest.captured_at - timedelta(days=7)
            minimum_7d = latest.captured_at - timedelta(days=8)
            choices_7d = [item for item in history if minimum_7d <= item.captured_at <= target_7d]
            if choices_7d:
                baseline_7d[key] = choices_7d[-1]

        previous_ranks: dict[tuple[str, str, str], int] = {}
        if current and len(baseline_24) == len(current):
            previous_order = sorted(
                current,
                key=lambda key: (
                    -baseline_24[key].level,
                    -(
                        baseline_24[key].experience
                        if baseline_24[key].experience is not None
                        else -1
                    ),
                    baseline_24[key].display_name.casefold(),
                ),
            )
            previous_ranks = {key: index + 1 for index, key in enumerate(previous_order)}

        output: list[SnapshotProgress] = []
        for key in ordered_keys:
            latest = current[key]
            prior = baseline_24.get(key)
            week = baseline_7d.get(key)
            new_achievements: tuple[AchievementRecord, ...] = ()
            profession_gains: tuple[tuple[str, int], ...] = ()
            if prior:
                previous_ids = {item.achievement_id for item in prior.achievements}
                new_achievements = tuple(
                    item for item in latest.achievements if item.achievement_id not in previous_ids
                )
                previous_professions = {item.key: item for item in prior.professions}
                gains: list[tuple[str, int]] = []
                for item in latest.professions:
                    old = previous_professions.get(item.key)
                    if old and item.skill_points > old.skill_points:
                        gains.append((item.display_name, item.skill_points - old.skill_points))
                profession_gains = tuple(sorted(gains))

            level_started_at: datetime | None = None
            history = grouped[key]
            for index in range(1, len(history)):
                if history[index].level > history[index - 1].level:
                    level_started_at = history[index].captured_at
            days_since_level = (
                round((latest.captured_at - level_started_at).total_seconds() / 86400, 3)
                if level_started_at
                else None
            )

            output.append(
                SnapshotProgress(
                    snapshot=latest,
                    baseline_24h_at=prior.captured_at if prior else None,
                    baseline_7d_at=week.captured_at if week else None,
                    levels_24h=_monotonic_delta(latest.level, prior.level) if prior else None,
                    levels_7d=_monotonic_delta(latest.level, week.level) if week else None,
                    experience_24h=(
                        _monotonic_delta(latest.experience, prior.experience)
                        if prior and latest.level == prior.level
                        else None
                    ),
                    deaths_24h=(
                        _monotonic_delta(latest.deaths.lifetime, prior.deaths.lifetime)
                        if prior
                        else None
                    ),
                    falling_deaths_24h=(
                        _monotonic_delta(latest.deaths.falling, prior.deaths.falling)
                        if prior
                        else None
                    ),
                    drowning_deaths_24h=(
                        _monotonic_delta(latest.deaths.drowning, prior.deaths.drowning)
                        if prior
                        else None
                    ),
                    fire_lava_deaths_24h=(
                        _monotonic_delta(latest.deaths.fire_lava, prior.deaths.fire_lava)
                        if prior
                        else None
                    ),
                    pvp_deaths_24h=(
                        _monotonic_delta(latest.deaths.pvp, prior.deaths.pvp)
                        if prior
                        else None
                    ),
                    dungeon_raid_deaths_24h=(
                        _monotonic_delta(
                            latest.deaths.dungeon_raid, prior.deaths.dungeon_raid
                        )
                        if prior
                        else None
                    ),
                    honorable_kills_24h=(
                        _monotonic_delta(latest.honorable_kills, prior.honorable_kills)
                        if prior
                        else None
                    ),
                    average_item_level_change_24h=(
                        _float_delta(latest.average_item_level, prior.average_item_level)
                        if prior
                        else None
                    ),
                    equipped_item_level_change_24h=(
                        _float_delta(latest.equipped_item_level, prior.equipped_item_level)
                        if prior
                        else None
                    ),
                    new_achievements_24h=new_achievements,
                    profession_skill_gains_24h=profession_gains,
                    rank=ranks[key],
                    rank_change=(previous_ranks[key] - ranks[key]) if key in previous_ranks else None,
                    days_since_last_level=days_since_level,
                )
            )
        return output

    async def save_commentary(
        self,
        guild_id: int,
        *,
        generated_at: datetime,
        text: str,
        source: str,
        story_angle: str,
    ) -> None:
        """Remember posted copy for anti-repetition, retaining only 30 entries."""

        async with self._lock:
            await asyncio.to_thread(
                self._save_commentary_sync,
                guild_id,
                generated_at,
                text,
                source,
                story_angle,
            )

    def _save_commentary_sync(
        self,
        guild_id: int,
        generated_at: datetime,
        text: str,
        source: str,
        story_angle: str,
    ) -> None:
        clean_text = str(text).strip()[:900]
        if not clean_text:
            return
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO commentary_history
                    (guild_id, generated_at, text, source, story_angle)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, generated_at) DO UPDATE SET
                    text=excluded.text,
                    source=excluded.source,
                    story_angle=excluded.story_angle
                """,
                (
                    guild_id,
                    _iso(generated_at),
                    clean_text,
                    str(source)[:40],
                    str(story_angle)[:80],
                ),
            )
            db.execute(
                """
                DELETE FROM commentary_history
                WHERE guild_id=? AND id NOT IN (
                    SELECT id FROM commentary_history
                    WHERE guild_id=? ORDER BY generated_at DESC, id DESC LIMIT 30
                )
                """,
                (guild_id, guild_id),
            )

    async def recent_commentary(
        self, guild_id: int, limit: int = 5
    ) -> list[CommentaryHistoryEntry]:
        async with self._lock:
            rows = await asyncio.to_thread(
                self._recent_commentary_sync, guild_id, min(20, max(1, int(limit)))
            )
        output: list[CommentaryHistoryEntry] = []
        for row in rows:
            generated_at = _parse_datetime(row["generated_at"])
            if generated_at is None:
                continue
            output.append(
                CommentaryHistoryEntry(
                    generated_at=generated_at,
                    text=str(row["text"]),
                    source=str(row["source"]),
                    story_angle=str(row["story_angle"]),
                )
            )
        return output

    def _recent_commentary_sync(self, guild_id: int, limit: int) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    """
                    SELECT generated_at, text, source, story_angle
                    FROM commentary_history WHERE guild_id=?
                    ORDER BY generated_at DESC, id DESC LIMIT ?
                    """,
                    (guild_id, limit),
                )
            ]

    async def set_schedule(self, schedule: DailySchedule) -> None:
        async with self._lock:
            await asyncio.to_thread(self._set_schedule_sync, schedule)

    def _set_schedule_sync(self, schedule: DailySchedule) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO schedules (guild_id, channel_id, time_of_day, timezone, next_run_utc)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id=excluded.channel_id,
                    time_of_day=excluded.time_of_day,
                    timezone=excluded.timezone,
                    next_run_utc=excluded.next_run_utc
                """,
                (
                    schedule.guild_id,
                    schedule.channel_id,
                    schedule.time_of_day,
                    schedule.timezone,
                    _iso(schedule.next_run_utc),
                ),
            )

    async def disable_schedule(self, guild_id: int) -> bool:
        async with self._lock:
            return await asyncio.to_thread(self._disable_schedule_sync, guild_id)

    def _disable_schedule_sync(self, guild_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM schedules WHERE guild_id=?", (guild_id,))
            return cursor.rowcount == 1

    async def due_schedules(self, now_utc: datetime) -> list[DailySchedule]:
        async with self._lock:
            rows = await asyncio.to_thread(self._due_schedules_sync, now_utc)
        return [self._schedule_from_row(row) for row in rows]

    def _due_schedules_sync(self, now_utc: datetime) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM schedules WHERE next_run_utc <= ? ORDER BY next_run_utc",
                    (_iso(now_utc),),
                )
            ]

    @staticmethod
    def _schedule_from_row(row: dict[str, Any]) -> DailySchedule:
        parsed = _parse_datetime(row["next_run_utc"])
        assert parsed is not None
        return DailySchedule(
            guild_id=int(row["guild_id"]),
            channel_id=int(row["channel_id"]),
            time_of_day=str(row["time_of_day"]),
            timezone=str(row["timezone"]),
            next_run_utc=parsed,
        )

    async def all_schedules(self) -> list[DailySchedule]:
        async with self._lock:
            rows = await asyncio.to_thread(self._all_schedules_sync)
        return [self._schedule_from_row(row) for row in rows]

    def _all_schedules_sync(self) -> Iterable[dict[str, Any]]:
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM schedules")]
