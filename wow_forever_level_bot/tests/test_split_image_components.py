from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import sys
import types

try:
    import discord  # noqa: F401
except ModuleNotFoundError:
    class _Item:
        pass

    class _TextDisplay(_Item):
        def __init__(self, content): self.data = {"type": 10, "content": content}

    class _Separator(_Item):
        def __init__(self, *, visible, spacing): self.data = {"type": 14, "divider": visible, "spacing": 1}

    class _MediaGalleryItem:
        def __init__(self, url, *, description): self.data = {"media": {"url": url}, "description": description}

    class _MediaGallery(_Item):
        def __init__(self, *items): self.data = {"type": 12, "items": [item.data for item in items]}

    class _Container(_Item):
        def __init__(self, *items, accent_colour): self.data = {"type": 17, "accent_color": int(accent_colour), "components": [item.data for item in items]}

    class _LayoutView:
        def __init__(self, timeout=None): self.items = []
        def add_item(self, item): self.items.append(item)
        def to_components(self): return [item.data for item in self.items]

    class _Colour:
        def __init__(self, value): self.value = value
        def __int__(self): return self.value
        @classmethod
        def blurple(cls): return cls(0x5865F2)

    fake = types.ModuleType("discord")
    fake.ui = types.SimpleNamespace(
        Item=_Item, LayoutView=_LayoutView, Container=_Container,
        TextDisplay=_TextDisplay, Separator=_Separator, MediaGallery=_MediaGallery,
    )
    fake.MediaGalleryItem = _MediaGalleryItem
    fake.SeparatorSpacing = types.SimpleNamespace(small=1)
    fake.Colour = _Colour
    sys.modules["discord"] = fake

from PIL import Image, ImageChops

from wow_forever_bot.components import build_split_image_components_v2_view
from wow_forever_bot.minimal_image_renderer import (
    render_minimal_leaderboard_chunks,
    render_minimal_leaderboard_png,
)

from test_minimal_image_renderer import _options, _rows


def test_18_rows_split_into_five_five_five_three_without_rescaling() -> None:
    generated_at = datetime(2026, 11, 16, tzinfo=timezone.utc)
    rows = _rows() * 6
    chunks = render_minimal_leaderboard_chunks(
        rows,
        options=_options(),
        generated_at=generated_at,
        rows_per_image=5,
    )
    images = [Image.open(BytesIO(chunk)).convert("RGB") for chunk in chunks]
    assert [image.size for image in images] == [
        (540, 278),
        (540, 278),
        (540, 278),
        (540, 170),
    ]

    source = Image.open(
        BytesIO(
            render_minimal_leaderboard_png(
                rows,
                options=_options(),
                generated_at=generated_at,
            )
        )
    ).convert("RGB")
    reconstructed = Image.new("RGB", (540, source.height - 8))
    y = 0
    for image in images:
        content = image.crop((0, 4, image.width, image.height - 4))
        reconstructed.paste(content, (0, y))
        y += content.height
    expected = source.crop((0, 4, source.width, source.height - 4))
    assert ImageChops.difference(expected, reconstructed).getbbox() is None


def test_split_image_components_v2_is_a_vertical_stack() -> None:
    filenames = [
        "wow-forever-leaderboard-01.png",
        "wow-forever-leaderboard-02.png",
        "wow-forever-leaderboard-03.png",
        "wow-forever-leaderboard-04.png",
    ]
    view = build_split_image_components_v2_view(
        filenames,
        commentary="@everyone Test commentary",
        total_rows=18,
    )
    payload = view.to_components()
    assert len(payload) == 1
    children = payload[0]["components"]
    galleries = [component for component in children if component["type"] == 12]
    assert len(galleries) == 4
    assert all(len(gallery["items"]) == 1 for gallery in galleries)
    assert [gallery["items"][0]["media"]["url"] for gallery in galleries] == [
        f"attachment://{filename}" for filename in filenames
    ]
    assert galleries[-1]["items"][0]["description"].endswith("ranks 16–18")
    assert sum(1 for component in children if component["type"] == 14) == 4
    assert len(children) + 1 == 11


def test_split_image_components_paginates_container_children_safely() -> None:
    filenames = [f"chunk-{index}.png" for index in range(10)]
    view = build_split_image_components_v2_view(
        filenames,
        commentary="test",
        total_rows=50,
    )
    payload = view.to_components()
    assert [len(container["components"]) for container in payload] == [10, 9, 1]
    assert all(len(container["components"]) <= 10 for container in payload)


def test_split_image_components_rejects_more_than_ten_attachments() -> None:
    filenames = [f"chunk-{index}.png" for index in range(11)]
    try:
        build_split_image_components_v2_view(
            filenames,
            commentary="test",
            total_rows=55,
        )
    except ValueError as exc:
        assert "at most 10" in str(exc)
    else:
        raise AssertionError("Expected the Discord attachment limit to be enforced")
