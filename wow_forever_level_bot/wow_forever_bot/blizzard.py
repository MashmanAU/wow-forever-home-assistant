from __future__ import annotations

import asyncio
import logging
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.parse import quote

import aiohttp

from .models import (
    AchievementRecord,
    CharacterProfile,
    CharacterSnapshot,
    DeathCounters,
    ProfessionProgress,
)

LOGGER = logging.getLogger("wow_forever_bot.blizzard")
SUPPORTED_REGIONS = ("us", "eu", "kr", "tw")
LOCALES = {"us": "en_US", "eu": "en_GB", "kr": "ko_KR", "tw": "zh_TW"}
SNAPSHOT_ENDPOINTS = {
    "achievements": "/achievements",
    "achievement-statistics": "/achievements/statistics",
    "professions": "/professions",
    "pvp-summary": "/pvp-summary",
}


class BlizzardAPIError(RuntimeError):
    """Base exception for Battle.net API failures."""


class CharacterNotFound(BlizzardAPIError):
    """The character is not visible in the WoW Forever Profile API."""


def character_slug(first_name: str, surname: str) -> str:
    combined = f"{first_name.strip()}-{surname.strip()}"
    normalised = unicodedata.normalize("NFKC", combined).casefold()
    normalised = re.sub(r"\s+", "-", normalised)
    normalised = re.sub(r"-+", "-", normalised).strip("-")
    if not normalised or "-" not in normalised:
        raise ValueError("Both first name and surname are required")
    return quote(normalised, safe="-")


def _name(value: Any) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("name")
        return str(candidate).strip() if candidate not in (None, "") else None
    if isinstance(value, str):
        return value.strip() or None
    return None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
        if abs(seconds) > 10_000_000_000:
            seconds /= 1000.0
        try:
            return datetime.fromtimestamp(seconds, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_achievements(payload: Any) -> tuple[AchievementRecord, ...]:
    if not isinstance(payload, dict) or not isinstance(payload.get("achievements"), list):
        return ()
    records: dict[int, AchievementRecord] = {}
    for item in payload["achievements"]:
        if not isinstance(item, dict):
            continue
        detail = item.get("achievement") if isinstance(item.get("achievement"), dict) else {}
        achievement_id = _integer(item.get("id")) or _integer(detail.get("id"))
        if achievement_id is None:
            continue
        name = _name(detail) or _name(item.get("name"))
        completed_at = _timestamp(
            item.get("completed_timestamp")
            or item.get("completed_at")
            or item.get("timestamp")
        )
        records[achievement_id] = AchievementRecord(achievement_id, name, completed_at)
    return tuple(records[key] for key in sorted(records))


def parse_professions(payload: Any) -> tuple[ProfessionProgress, ...]:
    if not isinstance(payload, dict):
        return ()
    records: dict[str, ProfessionProgress] = {}
    for group_name in ("primaries", "secondaries"):
        group = payload.get(group_name)
        if not isinstance(group, list):
            continue
        for profession in group:
            if not isinstance(profession, dict):
                continue
            profession_detail = (
                profession.get("profession")
                if isinstance(profession.get("profession"), dict)
                else profession
            )
            profession_name = _name(profession_detail) or _name(profession.get("name"))
            profession_id = _integer(profession_detail.get("id")) if isinstance(profession_detail, dict) else None
            if not profession_name:
                continue
            tiers = profession.get("tiers")
            if not isinstance(tiers, list) or not tiers:
                tiers = [profession]
            for tier in tiers:
                if not isinstance(tier, dict):
                    continue
                skill = _integer(tier.get("skill_points"))
                if skill is None:
                    continue
                tier_detail = tier.get("tier") if isinstance(tier.get("tier"), dict) else tier
                tier_name = _name(tier_detail) or _name(tier.get("name"))
                tier_id = _integer(tier_detail.get("id")) if isinstance(tier_detail, dict) else None
                identity = f"profession:{profession_id}" if profession_id is not None else f"profession-name:{profession_name.casefold()}"
                if tier_id is not None:
                    identity += f":tier:{tier_id}"
                elif tier_name:
                    identity += f":tier-name:{tier_name.casefold()}"
                records[identity] = ProfessionProgress(
                    key=identity,
                    profession_name=profession_name,
                    tier_name=tier_name,
                    skill_points=skill,
                    max_skill_points=_integer(tier.get("max_skill_points")),
                )
    return tuple(records[key] for key in sorted(records))


def _normalise_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _direct_named_metrics(category: dict[str, Any]) -> list[tuple[str, int, int | None]]:
    output: list[tuple[str, int, int | None]] = []
    statistics = category.get("statistics")
    if not isinstance(statistics, list):
        return output
    for statistic in statistics:
        if not isinstance(statistic, dict):
            continue
        label = _name(statistic.get("name")) or _name(statistic.get("statistic"))
        quantity = _integer(
            statistic.get("quantity")
            if statistic.get("quantity") is not None
            else statistic.get("value")
        )
        if label and quantity is not None:
            output.append((label, quantity, _integer(statistic.get("id"))))
    return output


def _all_named_metrics(node: Any) -> Iterable[tuple[str, int, int | None]]:
    if isinstance(node, dict):
        label = _name(node.get("name")) or _name(node.get("statistic"))
        quantity = _integer(node.get("quantity") if node.get("quantity") is not None else node.get("value"))
        if label and quantity is not None:
            yield label, quantity, _integer(node.get("id"))
        for child in node.values():
            yield from _all_named_metrics(child)
    elif isinstance(node, list):
        for child in node:
            yield from _all_named_metrics(child)


def parse_death_counters(payload: Any) -> DeathCounters:
    """Select death statistics by semantic category/name, never array position.

    The Forever response currently contains more than one statistic named
    ``Total deaths``. The lifetime counter is accepted from the known general
    statistic ID, the semantic ``Death Statistics`` category, or one unambiguous
    top-level candidate. This intentionally returns ``None`` rather than silently
    selecting a contextual PvP/dungeon aggregate.
    """

    if not isinstance(payload, dict):
        return DeathCounters()
    categories = payload.get("categories")
    if not isinstance(categories, list):
        categories = []

    lifetime_candidates: list[tuple[int, int]] = []
    unscored_totals: list[int] = []
    for category in categories:
        if not isinstance(category, dict):
            continue
        category_name = (
            _name(category.get("name"))
            or _name(category.get("category"))
            or ""
        )
        category_label = _normalise_label(category_name)
        for label, quantity, metric_id in _direct_named_metrics(category):
            if _normalise_label(label) != "total deaths":
                continue
            unscored_totals.append(quantity)
            score = 0
            # ID 60 is the Classic general lifetime "Total deaths" statistic
            # observed by the diagnostic.  Prefer the stable ID, then semantic
            # category names; never depend on a categories[] position.
            if metric_id == 60:
                score = 120
            elif category_label == "death statistics":
                score = 100
            elif category_label in {"death", "deaths"}:
                score = 80
            elif "death statistics" in category_label:
                score = 70
            elif "death" in category_label and not any(
                word in category_label
                for word in ("player", "pvp", "battleground", "dungeon", "raid")
            ):
                score = 50
            if score:
                lifetime_candidates.append((score, quantity))

    lifetime: int | None = None
    if lifetime_candidates:
        lifetime = max(lifetime_candidates, key=lambda item: item[0])[1]
    elif len(unscored_totals) == 1:
        lifetime = unscored_totals[0]

    by_label: dict[str, list[int]] = {}
    for label, quantity, _metric_id in _all_named_metrics(payload):
        by_label.setdefault(_normalise_label(label), []).append(quantity)

    def metric(*labels: str) -> int | None:
        for label in labels:
            values = by_label.get(_normalise_label(label))
            if values:
                return max(values)
        return None

    fire_lava = metric("Deaths from fire and lava", "Deaths from fire or lava")
    if fire_lava is None:
        fire = metric("Deaths from fire")
        lava = metric("Deaths from lava")
        if fire is not None or lava is not None:
            fire_lava = (fire or 0) + (lava or 0)

    return DeathCounters(
        lifetime=lifetime,
        falling=metric("Deaths from falling", "Deaths from falls"),
        drowning=metric("Deaths from drowning"),
        fire_lava=fire_lava,
        pvp=metric("Total deaths from other players"),
        dungeon_raid=metric("Total raid and dungeon deaths"),
    )


class BlizzardClient:
    """Async client for the undocumented WoW Forever profile namespace."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._session = session
        self._owns_session = session is None
        self._token: str | None = None
        self._token_expires_at = datetime.min.replace(tzinfo=timezone.utc)
        self._token_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=25)
            self._session = aiohttp.ClientSession(timeout=timeout)
            self._owns_session = True

    async def close(self) -> None:
        if self._session and self._owns_session and not self._session.closed:
            await self._session.close()
        if self._owns_session:
            self._session = None

    async def _access_token(self, force_refresh: bool = False) -> str:
        await self.start()
        now = datetime.now(timezone.utc)
        if not force_refresh and self._token and now < self._token_expires_at:
            return self._token
        async with self._token_lock:
            now = datetime.now(timezone.utc)
            if not force_refresh and self._token and now < self._token_expires_at:
                return self._token
            assert self._session is not None
            try:
                async with self._session.post(
                    "https://oauth.battle.net/token",
                    data={"grant_type": "client_credentials"},
                    auth=aiohttp.BasicAuth(self.client_id, self.client_secret),
                ) as response:
                    payload = await response.json(content_type=None)
                    if response.status != 200:
                        detail = payload.get("error_description") if isinstance(payload, dict) else response.reason
                        raise BlizzardAPIError(
                            f"Battle.net authentication failed ({response.status}): {detail or response.reason}"
                        )
            except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
                raise BlizzardAPIError(f"Could not authenticate with Battle.net: {exc}") from exc
            if not isinstance(payload, dict) or not payload.get("access_token"):
                raise BlizzardAPIError("Battle.net authentication returned no access token.")
            self._token = str(payload["access_token"])
            expires_in = max(60, int(payload.get("expires_in", 86400)) - 60)
            self._token_expires_at = now + timedelta(seconds=expires_in)
            return self._token

    @staticmethod
    def _validate_character(first_name: str, surname: str, region: str) -> tuple[str, str, str, str]:
        region = region.casefold().strip()
        if region not in SUPPORTED_REGIONS:
            raise BlizzardAPIError(f"Region must be one of: {', '.join(SUPPORTED_REGIONS)}.")
        first_name = first_name.strip()
        surname = surname.strip()
        if not first_name or not surname:
            raise CharacterNotFound("Both first name and surname are required.")
        return first_name, surname, region, character_slug(first_name, surname)

    async def _request_json(
        self,
        first_name: str,
        surname: str,
        region: str,
        suffix: str = "",
        endpoint_name: str = "profile",
    ) -> dict[str, Any]:
        first_name, surname, region, slug = self._validate_character(first_name, surname, region)
        await self.start()
        assert self._session is not None
        url = f"https://{region}.api.blizzard.com/profile/wow/character/{slug}{suffix}"
        params = {
            "namespace": f"profile-forever-{region}",
            "locale": LOCALES[region],
        }
        last_error: str | None = None
        for attempt in range(3):
            token = await self._access_token(force_refresh=attempt > 0 and last_error == "unauthorised")
            try:
                async with self._session.get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                ) as response:
                    try:
                        payload = await response.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError):
                        payload = {}
                    if response.status == 200 and isinstance(payload, dict):
                        return payload
                    if response.status == 404 and not suffix:
                        raise CharacterNotFound(
                            f"Could not find {first_name} {surname} in the {region.upper()} WoW Forever "
                            "profile service. Check the spelling, region, level-10 visibility "
                            "requirement and that the character has logged out recently."
                        )
                    if response.status == 401 and attempt < 2:
                        self._token = None
                        last_error = "unauthorised"
                        continue
                    detail = ""
                    if isinstance(payload, dict):
                        detail = str(payload.get("detail") or payload.get("title") or "")
                    if (response.status == 429 or response.status >= 500) and attempt < 2:
                        retry_after = response.headers.get("Retry-After", "1")
                        try:
                            delay = min(10.0, max(0.25, float(retry_after)))
                        except ValueError:
                            delay = 1.0
                        await asyncio.sleep(delay)
                        last_error = f"HTTP {response.status}"
                        continue
                    raise BlizzardAPIError(
                        f"Blizzard {endpoint_name} request failed ({response.status})"
                        + (f": {detail[:200]}" if detail else ".")
                    )
            except CharacterNotFound:
                raise
            except BlizzardAPIError:
                raise
            except asyncio.TimeoutError as exc:
                last_error = "request timed out"
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise BlizzardAPIError(f"Blizzard {endpoint_name} request timed out.") from exc
            except aiohttp.ClientError as exc:
                last_error = str(exc)
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise BlizzardAPIError(f"Could not connect to Blizzard {endpoint_name}: {exc}") from exc
        raise BlizzardAPIError(f"Blizzard {endpoint_name} request failed: {last_error or 'unknown error'}")

    @staticmethod
    def _profile_from_payload(
        payload: dict[str, Any], first_name: str, surname: str, region: str
    ) -> CharacterProfile:
        level = _integer(payload.get("level"))
        if level is None:
            raise BlizzardAPIError("Blizzard returned a profile without a valid level.")
        api_first = str(payload.get("first_name") or payload.get("name") or first_name).strip()
        api_surname = str(payload.get("surname") or surname).strip()
        return CharacterProfile(api_first, api_surname, region, level)

    async def get_character(
        self, first_name: str, surname: str, region: str = "us"
    ) -> CharacterProfile:
        first_name, surname, region, _slug = self._validate_character(first_name, surname, region)
        payload = await self._request_json(first_name, surname, region)
        return self._profile_from_payload(payload, first_name, surname, region)

    async def get_snapshot(
        self, first_name: str, surname: str, region: str = "us"
    ) -> CharacterSnapshot:
        """Collect a normalised snapshot, tolerating optional endpoint failures."""

        first_name, surname, region, _slug = self._validate_character(first_name, surname, region)
        profile_payload = await self._request_json(first_name, surname, region)
        profile = self._profile_from_payload(profile_payload, first_name, surname, region)
        documents: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        for endpoint_name, suffix in SNAPSHOT_ENDPOINTS.items():
            try:
                documents[endpoint_name] = await self._request_json(
                    first_name,
                    surname,
                    region,
                    suffix=suffix,
                    endpoint_name=endpoint_name,
                )
            except BlizzardAPIError as exc:
                LOGGER.warning(
                    "Snapshot endpoint %s failed for %s %s (%s): %s",
                    endpoint_name,
                    first_name,
                    surname,
                    region,
                    exc,
                )
                errors.append(f"{endpoint_name}: {exc}")
                documents[endpoint_name] = {}

        return CharacterSnapshot(
            first_name=profile.first_name,
            surname=profile.surname,
            region=profile.region,
            captured_at=datetime.now(timezone.utc),
            level=profile.level,
            character_id=_integer(profile_payload.get("id")),
            experience=_integer(profile_payload.get("experience")),
            average_item_level=_number(profile_payload.get("average_item_level")),
            equipped_item_level=_number(profile_payload.get("equipped_item_level")),
            last_login_at=_timestamp(profile_payload.get("last_login_timestamp")),
            character_class=_name(profile_payload.get("character_class")),
            race=_name(profile_payload.get("race")),
            faction=_name(profile_payload.get("faction")),
            ruleset=_name(profile_payload.get("ruleset")),
            honorable_kills=_integer(documents["pvp-summary"].get("honorable_kills")),
            deaths=parse_death_counters(documents["achievement-statistics"]),
            achievements=parse_achievements(documents["achievements"]),
            professions=parse_professions(documents["professions"]),
            source_errors=tuple(errors),
        )
