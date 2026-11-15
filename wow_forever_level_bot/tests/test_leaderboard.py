from dataclasses import replace
from datetime import datetime, timezone

from wow_forever_bot.commentary import CommentaryResult
from wow_forever_bot.daily import DailyBundle
from wow_forever_bot.models import (
    AchievementRecord,
    CharacterSnapshot,
    DeathCounters,
    ProfessionProgress,
    SnapshotProgress,
)
from wow_forever_bot.presentation import (
    daily_message_content,
    leaderboard_block,
    leaderboard_description,
)


def _row() -> SnapshotProgress:
    captured = datetime(2026, 11, 15, tzinfo=timezone.utc)
    snapshot = CharacterSnapshot(
        first_name="Mash",
        surname="Man",
        region="us",
        captured_at=captured,
        level=36,
        experience=900,
        character_class="Warrior",
        race="Human",
        honorable_kills=10,
        deaths=DeathCounters(lifetime=9),
        achievements=(AchievementRecord(2, "Going Up", captured),),
        professions=(
            ProfessionProgress(
                "profession:164:tier:2477",
                "Blacksmithing",
                "Classic",
                114,
                150,
            ),
        ),
    )
    return SnapshotProgress(
        snapshot=snapshot,
        levels_24h=2,
        levels_7d=5,
        experience_24h=400,
        deaths_24h=1,
        honorable_kills_24h=3,
        average_item_level_change_24h=2.5,
        new_achievements_24h=(AchievementRecord(2, "Going Up", captured),),
        profession_skill_gains_24h=(("Blacksmithing", 4),),
        rank=2,
        rank_change=1,
    )


def _bundle() -> DailyBundle:
    return DailyBundle(
        (_row(),),
        (),
        {},
        CommentaryResult(
            "Fresh facts from Azeroth.",
            "openai",
            story_angle="crafting-watch",
        ),
        datetime(2026, 11, 15, tzinfo=timezone.utc),
    )


def test_compact_layout_is_exactly_two_discord_markdown_lines() -> None:
    block = leaderboard_block(_row())
    lines = block.splitlines()
    assert len(lines) == 2
    assert lines[0] == "**#2 Mash Man** ↑1 · Human Warrior · Lv **36/60**"
    assert lines[1].startswith("↳ 💀 **9** · ⚒️ Blacksmithing **114/150**")
    for expected in (
        "24h Lv +2, 💀 +1, HK +3, iLvl +2.5",
        "7d Lv +5",
        "🏆 Going Up",
        "⚒️ Blacksmithing +4",
    ):
        assert expected in lines[1]


def test_missing_optional_data_keeps_clean_two_line_layout() -> None:
    row = _row()
    snapshot = replace(
        row.snapshot,
        character_class=None,
        race=None,
        deaths=DeathCounters(),
        professions=(),
    )
    quiet = replace(
        row,
        snapshot=snapshot,
        levels_24h=None,
        levels_7d=None,
        experience_24h=None,
        deaths_24h=None,
        honorable_kills_24h=None,
        average_item_level_change_24h=None,
        new_achievements_24h=(),
        profession_skill_gains_24h=(),
        rank=None,
        rank_change=None,
    )
    assert leaderboard_block(quiet) == "**Mash Man** · Lv **36/60**\n↳ 💀 **n/a**"


def test_every_character_stays_inside_one_embed_description() -> None:
    original = _row()
    rows = []
    for index in range(1, 21):
        snapshot = replace(
            original.snapshot,
            first_name=f"Mash{index}",
            surname="Man",
        )
        rows.append(replace(original, snapshot=snapshot, rank=index))
    description = leaderboard_description(rows)
    assert len(description) <= 4096
    assert description.count("\n") == 39
    assert "Mash1 Man" in description
    assert "Mash20 Man" in description


def test_commentary_is_normal_message_text() -> None:
    content = daily_message_content(_bundle(), mention_everyone=True)
    assert content == "@everyone\n\n📻 **WoW Forever daily**\n\nFresh facts from Azeroth."
