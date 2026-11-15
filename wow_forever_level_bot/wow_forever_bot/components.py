from __future__ import annotations

from typing import Any

import discord

from .models import SnapshotProgress
from .presentation import components_text_blocks


def build_components_v2_view(
    progress: tuple[SnapshotProgress, ...] | list[SnapshotProgress],
    *,
    options: Any,
) -> discord.ui.LayoutView:
    """Build a compact native Components V2 leaderboard.

    Character rows are packed three per TextDisplay. This keeps the complete
    layout comfortably below Discord's 40-component limit for normal rosters.
    """

    layout_type = getattr(discord.ui, "LayoutView", None)
    container_type = getattr(discord.ui, "Container", None)
    text_type = getattr(discord.ui, "TextDisplay", None)
    separator_type = getattr(discord.ui, "Separator", None)
    if not all((layout_type, container_type, text_type, separator_type)):
        raise RuntimeError("Components V2 requires discord.py 2.6 or newer")

    children: list[discord.ui.Item[Any]] = [
        text_type("## 🏆 WoW Forever leaderboard"),
        separator_type(visible=True, spacing=discord.SeparatorSpacing.small),
    ]
    blocks = components_text_blocks(progress, options=options, rows_per_block=3)
    for index, block in enumerate(blocks):
        children.append(text_type(block))
        if index != len(blocks) - 1:
            children.append(
                separator_type(visible=True, spacing=discord.SeparatorSpacing.small)
            )

    view = layout_type(timeout=None)
    view.add_item(
        container_type(
            *children,
            accent_colour=discord.Colour.blurple(),
        )
    )
    return view
