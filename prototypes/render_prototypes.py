#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "wow_forever_level_bot"))

from wow_forever_bot.config import Settings
from wow_forever_bot.image_renderer import render_leaderboard_png
from wow_forever_bot.models import CharacterSnapshot, DeathCounters, ProfessionProgress, SnapshotProgress
from wow_forever_bot.presentation import components_text_blocks, leaderboard_description

HERE = Path(__file__).resolve().parent


def load_rows() -> tuple[tuple[SnapshotProgress, ...], datetime]:
    data = json.loads((HERE / "current_leaderboard.json").read_text())
    captured = datetime.fromisoformat(data["captured_at"])
    rows = []
    for item in data["characters"]:
        first, surname = item["name"].split(" ", 1)
        professions = tuple(
            ProfessionProgress(
                f"prototype:{name.casefold().replace(' ', '-')}",
                name,
                "Classic",
                skill,
                maximum,
            )
            for name, skill, maximum in item["professions"]
        )
        snapshot = CharacterSnapshot(
            first,
            surname,
            "us",
            captured,
            item["level"],
            character_class=item["class"],
            race=item["race"],
            deaths=DeathCounters(lifetime=item["deaths"]),
            professions=professions,
        )
        rows.append(SnapshotProgress(snapshot=snapshot, rank=item["rank"]))
    return tuple(rows), captured


def main() -> None:
    rows, captured = load_rows()
    base = Settings("prototype", "prototype", "prototype")
    settings = replace(base, leaderboard_density="standard")
    description = leaderboard_description(rows, options=settings)
    native_payload = {
        "content": "📻 **WoW Forever daily**\n\n[announcer commentary remains normal Discord message text]",
        "embeds": [
            {
                "title": "🏆 WoW Forever leaderboard",
                "description": description,
                "color": 5793266,
            }
        ],
    }
    (HERE / "native_embed_payload.json").write_text(
        json.dumps(native_payload, indent=2, ensure_ascii=False) + "\n"
    )
    (HERE / "native_embed_preview.md").write_text(
        "# Option 1 — Improved native Discord embed\n\n"
        "📻 **WoW Forever daily**\n\n"
        "*[Announcer commentary is sent as normal message text.]*\n\n"
        "## 🏆 WoW Forever leaderboard\n\n"
        + description
        + "\n"
    )

    blocks = components_text_blocks(rows, options=settings, rows_per_block=3)
    components = [
        {"type": 10, "content": "## 🏆 WoW Forever leaderboard"},
        {"type": 14, "divider": True, "spacing": 1},
    ]
    for index, block in enumerate(blocks):
        components.append({"type": 10, "content": block})
        if index != len(blocks) - 1:
            components.append({"type": 14, "divider": True, "spacing": 1})
    component_payload = {
        "flags": 32768,
        "components": [{"type": 17, "accent_color": 5793266, "components": components}],
    }
    (HERE / "components_v2_payload.json").write_text(
        json.dumps(component_payload, indent=2, ensure_ascii=False) + "\n"
    )
    (HERE / "components_v2_preview.md").write_text(
        "# Option 2 — Discord Components V2 compact layout\n\n"
        "The announcer commentary is a separate normal Discord message because Components V2 "
        "cannot share a message with top-level content.\n\n"
        "## 🏆 WoW Forever leaderboard\n\n"
        + "\n\n---\n\n".join(blocks)
        + "\n"
    )

    png = render_leaderboard_png(rows, options=settings, generated_at=captured)
    (HERE / "image_two_column_preview.png").write_bytes(png)


if __name__ == "__main__":
    main()
