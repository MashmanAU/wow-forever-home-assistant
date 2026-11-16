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


def build_split_image_components_v2_view(
    image_filenames: list[str] | tuple[str, ...],
    *,
    commentary: str,
    total_rows: int,
) -> discord.ui.LayoutView:
    """Build a vertical Components V2 stack of short leaderboard images.

    Every attachment is placed in its own one-item Media Gallery. This is
    intentional: a single multi-item gallery can become a grid and shrink the
    images, recreating the problem this delivery mode is designed to avoid.
    """

    if not image_filenames:
        raise ValueError("At least one split leaderboard image is required")
    if total_rows < 1:
        raise ValueError("total_rows must be at least 1")
    if len(image_filenames) > 10:
        raise ValueError("Discord supports at most 10 uploaded files per message")

    layout_type = getattr(discord.ui, "LayoutView", None)
    container_type = getattr(discord.ui, "Container", None)
    text_type = getattr(discord.ui, "TextDisplay", None)
    separator_type = getattr(discord.ui, "Separator", None)
    gallery_type = getattr(discord.ui, "MediaGallery", None)
    gallery_item_type = getattr(discord, "MediaGalleryItem", None)
    if not all(
        (
            layout_type,
            container_type,
            text_type,
            separator_type,
            gallery_type,
            gallery_item_type,
        )
    ):
        raise RuntimeError("Split-image Components V2 requires discord.py 2.6 or newer")

    view = layout_type(timeout=None)
    # A Container accepts at most 10 children. The first card has three heading
    # items and therefore holds four galleries; continuation cards hold five.
    offset = 0
    first = True
    while offset < len(image_filenames):
        capacity = 4 if first else 5
        batch = image_filenames[offset : offset + capacity]
        children: list[discord.ui.Item[Any]] = []
        if first:
            children.extend(
                [
                    text_type("## 🏆 WoW Forever leaderboard"),
                    text_type(commentary),
                    separator_type(
                        visible=True,
                        spacing=discord.SeparatorSpacing.small,
                    ),
                ]
            )
        for local_index, filename in enumerate(batch):
            global_index = offset + local_index
            start_rank = global_index * 5 + 1
            end_rank = min(start_rank + 4, total_rows)
            children.append(
                gallery_type(
                    gallery_item_type(
                        f"attachment://{filename}",
                        description=(
                            f"WoW Forever leaderboard ranks {start_rank}–{end_rank}"
                        ),
                    )
                )
            )
            if local_index != len(batch) - 1:
                children.append(
                    separator_type(
                        visible=False,
                        spacing=discord.SeparatorSpacing.small,
                    )
                )
        view.add_item(
            container_type(
                *children,
                accent_colour=discord.Colour(0xC79C6E),
            )
        )
        offset += len(batch)
        first = False
    return view
