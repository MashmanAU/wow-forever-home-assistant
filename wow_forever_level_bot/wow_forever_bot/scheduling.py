from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import RefreshResult, TrackedCharacter


def parse_daily_time(value: str) -> time:
    value = value.strip()
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError("Time must use 24-hour HH:MM format, for example 20:30.") from exc
    return parsed.replace(second=0, microsecond=0)


def next_daily_run(
    time_of_day: str,
    timezone_name: str,
    *,
    now_utc: datetime | None = None,
) -> datetime:
    """Return the next daily run in UTC, preserving local wall-clock time across DST."""
    scheduled_time = parse_daily_time(time_of_day)
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            "Timezone must be a valid IANA name, for example Australia/Sydney."
        ) from exc

    current_utc = now_utc or datetime.now(timezone.utc)
    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(tzinfo=timezone.utc)
    local_now = current_utc.astimezone(zone)
    target_date: date = local_now.date()
    candidate = datetime.combine(target_date, scheduled_time, tzinfo=zone)
    if candidate <= local_now:
        candidate = datetime.combine(target_date + timedelta(days=1), scheduled_time, tzinfo=zone)

    # A DST jump can make a wall-clock time nonexistent. Round-trip and use the
    # first valid local time after the jump rather than silently skipping a day.
    round_tripped = candidate.astimezone(timezone.utc).astimezone(zone)
    if (round_tripped.hour, round_tripped.minute) != (
        scheduled_time.hour,
        scheduled_time.minute,
    ):
        candidate = round_tripped
    return candidate.astimezone(timezone.utc)


def sort_tracked_characters(
    characters: list[TrackedCharacter],
) -> list[TrackedCharacter]:
    """Highest level first; unknown levels last; alphabetical for equal levels."""
    return sorted(
        characters,
        key=lambda item: (
            item.level is None,
            -(item.level if item.level is not None else -1),
            item.display_name.casefold(),
            item.region,
        ),
    )


def sort_refresh_results(results: list[RefreshResult]) -> list[RefreshResult]:
    return sorted(
        results,
        key=lambda item: (
            item.character.level is None,
            -(item.character.level if item.character.level is not None else -1),
            item.character.display_name.casefold(),
            item.character.region,
        ),
    )
