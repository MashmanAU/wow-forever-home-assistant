from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime, timezone
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .blizzard import BlizzardAPIError, BlizzardClient, CharacterNotFound
from .commentary import CommentaryService
from .components import build_split_image_components_v2_view
from .config import Settings
from .daily import (
    DailyBundle,
    build_fixture_daily_bundle,
    build_fixture_live_news_bundle,
    build_live_daily_bundle,
    build_live_test_daily_bundle,
)
from .models import (
    CharacterProfile,
    CharacterSnapshot,
    DailySchedule,
    RefreshResult,
    TrackedCharacter,
)
from .minimal_image_renderer import render_minimal_leaderboard_chunks
from .news import WowheadNewsClient
from .presentation import daily_message_content, leaderboard_description
from .table_renderer import leaderboard_table_code_blocks
from .scheduling import (
    next_daily_run,
    parse_daily_time,
    sort_refresh_results,
    sort_tracked_characters,
)
from .store import Store

LOGGER = logging.getLogger("wow_forever_bot")
Region = Literal["us", "eu", "kr", "tw"]
PreviewScenario = Literal[
    "radio-day",
    "quiet-day",
    "comeback",
    "crafting-day",
    "pvp-night",
]

class ForeverBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self.store = Store(settings.database_path, settings.default_timezone)
        self.blizzard = BlizzardClient(
            settings.blizzard_client_id, settings.blizzard_client_secret
        )
        self.news = WowheadNewsClient(
            settings.wowhead_feed_url,
            keywords=settings.wowhead_keywords,
        )
        self.commentary = CommentaryService(
            settings.openai_api_key,
            model=settings.openai_model,
            max_words=settings.commentary_max_words,
            roast_level=settings.commentary_roast_level,
            announcer_style=settings.announcer_style,
            custom_style_notes=settings.announcer_custom_notes,
            news_emphasis=settings.commentary_news_emphasis,
            character_banter=settings.commentary_character_banter,
        )

    async def setup_hook(self) -> None:
        await self.store.initialize()
        await self.blizzard.start()
        await self.add_cog(ForeverCommands(self))
        synced = await self.tree.sync()
        LOGGER.info("Synced %s global commands", len(synced))

    async def on_ready(self) -> None:
        if self.user:
            LOGGER.info("Logged in as %s (%s)", self.user, self.user.id)

    async def close(self) -> None:
        await self.commentary.close()
        await self.news.close()
        await self.blizzard.close()
        await super().close()


class ForeverCommands(commands.Cog):
    def __init__(self, bot: ForeverBot) -> None:
        self.bot = bot
        self.schedule_worker.change_interval(
            seconds=bot.settings.schedule_check_seconds
        )
        self.schedule_worker.start()

    def cog_unload(self) -> None:
        self.schedule_worker.cancel()

    async def _refresh_guild(self, guild_id: int) -> list[RefreshResult]:
        characters = await self.bot.store.list_characters(guild_id)
        results: list[RefreshResult] = []
        for character in characters:
            try:
                snapshot = await self.bot.blizzard.get_snapshot(
                    character.first_name, character.surname, character.region
                )
                profile = snapshot.profile
                await self.bot.store.update_character(guild_id, profile)
                await self.bot.store.save_snapshot(guild_id, snapshot)
                if snapshot.source_errors:
                    LOGGER.warning(
                        "Saved a partial snapshot for %s: %s",
                        snapshot.display_name,
                        "; ".join(snapshot.source_errors),
                    )
                refreshed = TrackedCharacter(
                    guild_id=guild_id,
                    first_name=profile.first_name,
                    surname=profile.surname,
                    region=profile.region,
                    level=profile.level,
                    last_checked_at=datetime.now(timezone.utc),
                )
                results.append(
                    RefreshResult(
                        character=refreshed,
                        previous_level=character.level,
                    )
                )
            except BlizzardAPIError as exc:
                LOGGER.warning(
                    "Could not refresh %s %s (%s): %s",
                    character.first_name,
                    character.surname,
                    character.region,
                    exc,
                )
                results.append(
                    RefreshResult(
                        character=character,
                        previous_level=character.level,
                        error=str(exc),
                    )
                )
        return sort_refresh_results(results)

    async def _fetch_live_snapshots_read_only(
        self, guild_id: int
    ) -> tuple[list[CharacterSnapshot], list[str]]:
        """Fetch every tracked character without updating characters or snapshot history."""

        characters = await self.bot.store.list_characters(guild_id)
        snapshots: list[CharacterSnapshot] = []
        errors: list[str] = []
        for character in characters:
            try:
                snapshots.append(
                    await self.bot.blizzard.get_snapshot(
                        character.first_name,
                        character.surname,
                        character.region,
                    )
                )
            except BlizzardAPIError as exc:
                errors.append(
                    f"{character.display_name} ({character.region.upper()}): {exc}"
                )
        return snapshots, errors

    @staticmethod
    def _report_embeds(results: list[RefreshResult]) -> list[discord.Embed]:
        if not results:
            return [
                discord.Embed(
                    title="WoW Forever levels",
                    description="No characters are currently being tracked.",
                    colour=discord.Colour.blurple(),
                )
            ]

        embeds: list[discord.Embed] = []
        for offset in range(0, len(results), 25):
            batch = results[offset : offset + 25]
            title = "WoW Forever levels"
            if offset:
                title += f" — continued ({offset + 1}–{offset + len(batch)})"
            embed = discord.Embed(title=title, colour=discord.Colour.blurple())
            for result in batch:
                level_text = (
                    f"Level **{result.character.level}**"
                    if result.character.level is not None
                    else "Level unavailable"
                )
                if result.increase:
                    level_text += f"  ·  **+{result.increase}** since the previous check"
                if result.error:
                    level_text += "\n⚠️ Refresh failed; showing the last known level."
                embed.add_field(
                    name=f"{result.character.display_name} · {result.character.region.upper()}",
                    value=level_text,
                    inline=False,
                )
            embeds.append(embed)
        return embeds

    @staticmethod
    def _cached_embeds(characters: list[TrackedCharacter]) -> list[discord.Embed]:
        ordered = sort_tracked_characters(characters)
        results = [
            RefreshResult(character=character, previous_level=character.level)
            for character in ordered
        ]
        return ForeverCommands._report_embeds(results)

    @staticmethod
    def _daily_message_content(
        bundle: DailyBundle,
        *,
        mention_everyone: bool = False,
        notice: str | None = None,
    ) -> str:
        return daily_message_content(
            bundle,
            mention_everyone=mention_everyone,
            notice=notice,
        )

    def _leaderboard_embed(self, bundle: DailyBundle) -> discord.Embed:
        return discord.Embed(
            title="🏆 WoW Forever leaderboard",
            description=leaderboard_description(
                list(bundle.progress),
                options=self.bot.settings,
            ),
            colour=discord.Colour.blurple(),
        )

    @staticmethod
    def _news_embed(bundle: DailyBundle) -> discord.Embed | None:
        if not bundle.news:
            return None
        news_lines = [f"• [{item.title}]({item.url})" for item in bundle.news[:5]]
        return discord.Embed(
            title="📰 Wowhead — WoW Forever",
            description="\n".join(news_lines),
            colour=discord.Colour.orange(),
        )

    def _daily_embeds(self, bundle: DailyBundle) -> list[discord.Embed]:
        """Native text rendition retained as a selectable mode and safe fallback."""

        embeds = [self._leaderboard_embed(bundle)]
        news = self._news_embed(bundle)
        if news is not None:
            embeds.append(news)
        return embeds

    def _table_embeds(self, bundle: DailyBundle) -> list[discord.Embed]:
        blocks = leaderboard_table_code_blocks(
            bundle.progress,
            options=self.bot.settings,
        )
        embeds = [
            discord.Embed(
                title=(
                    "🏆 WoW Forever leaderboard"
                    if index == 0
                    else "🏆 WoW Forever leaderboard — continued"
                ),
                description=block,
                colour=discord.Colour.blurple(),
            )
            for index, block in enumerate(blocks)
        ]
        news = self._news_embed(bundle)
        if news is not None:
            embeds.append(news)
        return embeds

    def _private_test_channel(
        self,
        guild: discord.Guild,
    ) -> tuple[discord.TextChannel | None, str | None]:
        """Resolve the configured private test channel without touching schedules."""

        channel_name = self.bot.settings.test_channel_name
        matches = [
            channel for channel in guild.text_channels if channel.name == channel_name
        ]
        if len(matches) == 1:
            return matches[0], None
        if not matches:
            return None, (
                f"No text channel named **#{channel_name}** exists. "
                "Create it or update **Private test channel** in Home Assistant."
            )
        return None, (
            f"More than one text channel is named **#{channel_name}**. "
            "Rename duplicates before running a test."
        )

    async def _send_daily_report(
        self,
        channel: discord.abc.Messageable,
        bundle: DailyBundle,
        *,
        mention_everyone: bool = False,
        notice: str | None = None,
        allowed_mentions: discord.AllowedMentions | None = None,
    ) -> str:
        """Send the configured production layout and return the mode actually used.

        Scheduled delivery and both test commands call this method, which prevents
        preview drift. Split-image Components V2 places commentary in a Text Display.
        """

        mentions = allowed_mentions or discord.AllowedMentions.none()
        content = self._daily_message_content(
            bundle,
            mention_everyone=mention_everyone,
            notice=notice,
        )
        mode = self.bot.settings.leaderboard_render_mode
        news = self._news_embed(bundle)

        if mode == "split_image":
            try:
                png_chunks = render_minimal_leaderboard_chunks(
                    bundle.progress,
                    options=self.bot.settings,
                    generated_at=bundle.generated_at,
                    rows_per_image=self.bot.settings.split_image_rows,
                )
                filenames = [
                    f"wow-forever-leaderboard-{index:02d}.png"
                    for index in range(1, len(png_chunks) + 1)
                ]
                files = [
                    discord.File(io.BytesIO(png), filename=filename)
                    for png, filename in zip(png_chunks, filenames, strict=True)
                ]
                view = build_split_image_components_v2_view(
                    filenames,
                    commentary=content,
                    total_rows=len(bundle.progress),
                    rows_per_image=self.bot.settings.split_image_rows,
                )
                await channel.send(
                    view=view,
                    files=files,
                    allowed_mentions=mentions,
                )
                if news is not None:
                    await channel.send(
                        embed=news,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                return "split_image"
            except Exception:
                LOGGER.exception(
                    "Split-image Components V2 delivery failed; using the native text fallback"
                )
                await channel.send(
                    content=content,
                    embeds=self._daily_embeds(bundle),
                    allowed_mentions=mentions,
                )
                return "native_embed_fallback"

        if mode == "table":
            try:
                await channel.send(
                    content=content,
                    embeds=self._table_embeds(bundle),
                    allowed_mentions=mentions,
                )
                return "table"
            except Exception:
                LOGGER.exception(
                    "Table leaderboard rendering failed; using the native text fallback"
                )
                await channel.send(
                    content=content,
                    embeds=self._daily_embeds(bundle),
                    allowed_mentions=mentions,
                )
                return "native_embed_fallback"

        await channel.send(
            content=content,
            embeds=self._daily_embeds(bundle),
            allowed_mentions=mentions,
        )
        return "native_embed"

    @tasks.loop(seconds=60)
    async def schedule_worker(self) -> None:
        now = datetime.now(timezone.utc)
        for schedule in await self.bot.store.due_schedules(now):
            try:
                channel = self.bot.get_channel(schedule.channel_id)
                if channel is None:
                    channel = await self.bot.fetch_channel(schedule.channel_id)
                if not isinstance(channel, discord.TextChannel):
                    raise RuntimeError("Configured destination is not a text channel")
                results = await self._refresh_guild(schedule.guild_id)
                embeds = self._report_embeds(results)
                daily: DailyBundle | None = None
                content = "@everyone"
                if self.bot.settings.commentary_enabled:
                    try:
                        daily = await build_live_daily_bundle(
                            self.bot.store,
                            schedule.guild_id,
                            self.bot.news,
                            self.bot.commentary,
                            news_lookback_hours=self.bot.settings.wowhead_lookback_hours,
                        )
                        embeds = self._daily_embeds(daily)
                        content = self._daily_message_content(
                            daily,
                            mention_everyone=True,
                        )
                    except Exception:
                        LOGGER.exception(
                            "Daily commentary assembly failed; posting factual level fallback"
                        )
                if daily is not None:
                    await self._send_daily_report(
                        channel,
                        daily,
                        mention_everyone=True,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=True,
                            users=False,
                            roles=False,
                            replied_user=False,
                        ),
                    )
                else:
                    await channel.send(
                        content=content,
                        embeds=embeds,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=True,
                            users=False,
                            roles=False,
                            replied_user=False,
                        ),
                    )
                if daily is not None:
                    try:
                        await self.bot.store.save_commentary(
                            schedule.guild_id,
                            generated_at=daily.generated_at,
                            text=daily.commentary.text,
                            source=daily.commentary.source,
                            story_angle=daily.commentary.story_angle,
                        )
                    except Exception:
                        LOGGER.exception(
                            "Daily report posted, but commentary style memory could not be saved"
                        )
                LOGGER.info(
                    "Posted scheduled level report for guild %s to channel %s",
                    schedule.guild_id,
                    schedule.channel_id,
                )
            except Exception:
                LOGGER.exception(
                    "Scheduled report failed for guild %s", schedule.guild_id
                )
            finally:
                # Advance from the current time, not the old due time, so a bot that
                # was offline does not send several catch-up notifications.
                try:
                    following_run = next_daily_run(
                        schedule.time_of_day,
                        schedule.timezone,
                        now_utc=datetime.now(timezone.utc),
                    )
                    await self.bot.store.set_schedule(
                        DailySchedule(
                            guild_id=schedule.guild_id,
                            channel_id=schedule.channel_id,
                            time_of_day=schedule.time_of_day,
                            timezone=schedule.timezone,
                            next_run_utc=following_run,
                        )
                    )
                except Exception:
                    LOGGER.exception(
                        "Could not advance schedule for guild %s", schedule.guild_id
                    )

    @schedule_worker.before_loop
    async def before_schedule_worker(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="character-add",
        description="Verify a WoW Forever character and add it to this server's tracking list.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        first_name="Character first name",
        surname="Character surname",
        region="Battle.net region",
    )
    async def character_add(
        self,
        interaction: discord.Interaction,
        first_name: str,
        surname: str,
        region: Region = "us",
    ) -> None:
        assert interaction.guild_id is not None
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            snapshot = await self.bot.blizzard.get_snapshot(
                first_name, surname, region
            )
            profile = snapshot.profile
            added = await self.bot.store.add_character(
                interaction.guild_id, profile, interaction.user.id
            )
            if added:
                await self.bot.store.save_snapshot(interaction.guild_id, snapshot)
        except (CharacterNotFound, BlizzardAPIError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        if added:
            await interaction.followup.send(
                f"Added **{profile.display_name}** ({profile.region.upper()}), "
                f"currently level **{profile.level}**.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"**{profile.display_name}** ({profile.region.upper()}) is already tracked.",
                ephemeral=True,
            )

    @app_commands.command(
        name="character-remove",
        description="Remove a character from this server's tracking list.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def character_remove(
        self,
        interaction: discord.Interaction,
        first_name: str,
        surname: str,
        region: Region = "us",
    ) -> None:
        assert interaction.guild_id is not None
        removed = await self.bot.store.remove_character(
            interaction.guild_id, first_name, surname, region
        )
        message = (
            f"Removed **{first_name} {surname}** ({region.upper()})."
            if removed
            else "That character is not in this server's tracking list."
        )
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(
        name="characters",
        description="Show the currently tracked WoW Forever characters (cached level).",
    )
    @app_commands.guild_only()
    async def characters(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        characters = await self.bot.store.list_characters(interaction.guild_id)
        await interaction.response.send_message(
            embeds=self._cached_embeds(characters), ephemeral=False
        )

    @app_commands.command(
        name="level",
        description="Look up one WoW Forever character without adding it to the list.",
    )
    async def level(
        self,
        interaction: discord.Interaction,
        first_name: str,
        surname: str,
        region: Region = "us",
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            profile = await self.bot.blizzard.get_character(
                first_name, surname, region
            )
        except (CharacterNotFound, BlizzardAPIError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        embed = discord.Embed(
            title=profile.display_name,
            description=f"Level **{profile.level}** · {profile.region.upper()}",
            colour=discord.Colour.green(),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="levels",
        description="Refresh and report all tracked WoW Forever character levels now.",
    )
    @app_commands.guild_only()
    async def levels(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        await interaction.response.defer(thinking=True)
        results = await self._refresh_guild(interaction.guild_id)
        await interaction.followup.send(embeds=self._report_embeds(results))

    @app_commands.command(
        name="daily-preview",
        description="Privately preview AI commentary using deterministic synthetic history.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        scenario="Synthetic snapshot scenario; no live database data is read or changed"
    )
    async def daily_preview(
        self,
        interaction: discord.Interaction,
        scenario: PreviewScenario = "radio-day",
    ) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        bundle = await build_fixture_daily_bundle(
            self.bot.commentary,
            scenario=scenario,
        )
        await interaction.followup.send(
            content=self._daily_message_content(
                bundle,
                notice=(
                    "🧪 **Synthetic preview only.** This used a disposable test database, "
                    "fixed fixture history and synthetic Wowhead headlines. The live bot database "
                    "and schedule were not read or changed."
                ),
            ),
            embeds=self._daily_embeds(bundle),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="daily-post-test",
        description="Post synthetic characters with live Wowhead news to the private test channel.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        scenario="Synthetic character scenario; live database and schedule remain untouched",
    )
    async def daily_post_test(
        self,
        interaction: discord.Interaction,
        scenario: PreviewScenario = "radio-day",
    ) -> None:
        assert interaction.guild_id is not None
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only run inside a server.", ephemeral=True
            )
            return
        channel, channel_error = self._private_test_channel(guild)
        if channel is None:
            await interaction.response.send_message(
                channel_error or "The private test channel could not be resolved.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if guild.me:
            permissions = channel.permissions_for(guild.me)
            missing = []
            if not permissions.view_channel:
                missing.append("View Channel")
            if not permissions.send_messages:
                missing.append("Send Messages")
            if not permissions.embed_links:
                missing.append("Embed Links")
            if missing:
                await interaction.response.send_message(
                    "I cannot post the test until my role has: "
                    + ", ".join(f"**{item}**" for item in missing)
                    + ".",
                    ephemeral=True,
                )
                return
        await interaction.response.defer(ephemeral=True, thinking=True)
        bundle = await build_fixture_live_news_bundle(
            self.bot.news,
            self.bot.commentary,
            scenario=scenario,
            news_lookback_hours=self.bot.settings.wowhead_lookback_hours,
        )
        actual_mode = await self._send_daily_report(
            channel,
            bundle,
            notice=(
                "🧪 **Isolated test report.** Synthetic character history, live Wowhead RSS, "
                "no live database or schedule access, and no notifications."
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        news_status = (
            "Live Wowhead RSS was unavailable; the report continued without news."
            if bundle.news_error
            else f"Live Wowhead RSS returned {len(bundle.news)} matching headline(s)."
        )
        await interaction.followup.send(
            f"Posted the **{scenario}** isolated test to {channel.mention}. "
            f"{news_status} Commentary: **{bundle.commentary.source}**. "
            f"Layout: **{actual_mode}**. "
            "The live schedule and database were untouched, and mentions were suppressed.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="daily-live-test",
        description="Post a read-only live-data rehearsal to the configured private test channel.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def daily_live_test(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only run inside a server.", ephemeral=True
            )
            return

        channel, channel_error = self._private_test_channel(guild)
        if channel is None:
            await interaction.response.send_message(
                channel_error or "The private test channel could not be resolved.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if guild.me:
            permissions = channel.permissions_for(guild.me)
            missing = []
            if not permissions.view_channel:
                missing.append("View Channel")
            if not permissions.send_messages:
                missing.append("Send Messages")
            if not permissions.embed_links:
                missing.append("Embed Links")
            if missing:
                await interaction.response.send_message(
                    "I cannot post the live test until my role has: "
                    + ", ".join(f"**{item}**" for item in missing)
                    + ".",
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return

        await interaction.response.defer(ephemeral=True, thinking=True)
        snapshots, errors = await self._fetch_live_snapshots_read_only(
            interaction.guild_id
        )
        if errors:
            await interaction.followup.send(
                "No test was posted because current Blizzard data could not be fetched "
                "for every tracked character:\n" + "\n".join(f"• {item}" for item in errors),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if not snapshots:
            await interaction.followup.send(
                "No test was posted because this server has no tracked characters.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        bundle = await build_live_test_daily_bundle(
            self.bot.store,
            interaction.guild_id,
            snapshots,
            self.bot.news,
            self.bot.commentary,
            news_lookback_hours=self.bot.settings.wowhead_lookback_hours,
        )
        actual_mode = await self._send_daily_report(
            channel,
            bundle,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        news_status = (
            "Live Wowhead RSS was unavailable; the factual report continued without news."
            if bundle.news_error
            else f"Live Wowhead RSS returned {len(bundle.news)} matching headline(s)."
        )
        partial_count = sum(bool(item.source_errors) for item in snapshots)
        partial_status = (
            f" {partial_count} character snapshot(s) had optional Blizzard fields unavailable."
            if partial_count
            else ""
        )
        await interaction.followup.send(
            f"Posted the read-only live test to **#{self.bot.settings.test_channel_name}**. "
            f"{news_status} Commentary: **{bundle.commentary.source}**. "
            f"Layout: **{actual_mode}**.{partial_status} "
            "No snapshot, 24-hour baseline, commentary history, schedule or next-run value was changed, "
            "and all mentions were suppressed.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="schedule",
        description="Post an @everyone level report every day at a specific local time.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.rename(scheduled_time="time", timezone_name="timezone")
    @app_commands.describe(
        channel="Text channel for the daily report",
        scheduled_time="Daily time in 24-hour HH:MM format, e.g. 20:30",
        timezone_name="IANA timezone, e.g. Australia/Sydney",
    )
    async def schedule(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        scheduled_time: str,
        timezone_name: str = "Australia/Sydney",
    ) -> None:
        assert interaction.guild_id is not None
        if interaction.guild and interaction.guild.me:
            permissions = channel.permissions_for(interaction.guild.me)
            missing = []
            if not permissions.view_channel:
                missing.append("View Channel")
            if not permissions.send_messages:
                missing.append("Send Messages")
            if not permissions.embed_links:
                missing.append("Embed Links")
            if not permissions.mention_everyone:
                missing.append("Mention @everyone, @here and All Roles")
            if missing:
                await interaction.response.send_message(
                    "I cannot schedule the report in that channel until my role has: "
                    + ", ".join(f"**{item}**" for item in missing)
                    + ".",
                    ephemeral=True,
                )
                return
        try:
            normalised_time = parse_daily_time(scheduled_time).strftime("%H:%M")
            next_run = next_daily_run(normalised_time, timezone_name)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        await self.bot.store.set_schedule(
            DailySchedule(
                guild_id=interaction.guild_id,
                channel_id=channel.id,
                time_of_day=normalised_time,
                timezone=timezone_name,
                next_run_utc=next_run,
            )
        )
        await interaction.response.send_message(
            f"Daily report scheduled for {discord.utils.format_dt(next_run, style='F')} "
            f"in {channel.mention}, then every day at **{normalised_time}** "
            f"(**{timezone_name}**). Each scheduled report will notify **@everyone**.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="schedule-off",
        description="Disable automatic WoW Forever level reports for this server.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def schedule_off(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        removed = await self.bot.store.disable_schedule(interaction.guild_id)
        await interaction.response.send_message(
            "Daily level reports are now disabled."
            if removed
            else "No daily level report was configured.",
            ephemeral=True,
        )

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "You need the **Manage Server** permission to use this command."
        else:
            LOGGER.exception("Application command failed", exc_info=error)
            message = "The command failed unexpectedly. Check the Home Assistant app log."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def run_bot(settings: Settings) -> None:
    bot = ForeverBot(settings)
    async with bot:
        await bot.start(settings.discord_token)
