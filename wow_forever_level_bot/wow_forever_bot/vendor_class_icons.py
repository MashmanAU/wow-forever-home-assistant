"""Vendor the pinned Unlicensed WoW class-icon set during the container build."""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_COMMIT = "5d9ad053876920138f68d69a4197fc18771b9505"
SOURCE_ROOT = (
    "https://raw.githubusercontent.com/orourkek/Wow-Icons/"
    f"{SOURCE_COMMIT}/images/class/64"
)
CLASS_ICON_FILES = (
    "druid.png",
    "hunter.png",
    "mage.png",
    "paladin.png",
    "priest.png",
    "rogue.png",
    "shaman.png",
    "warlock.png",
    "warrior.png",
)


def validate_png(data: bytes, *, expected_size: tuple[int, int] = (64, 64)) -> None:
    """Reject HTML/error responses and any unexpected source dimensions."""

    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("downloaded class icon is not a valid PNG")
    offset = 8
    dimensions: tuple[int, int] | None = None
    saw_iend = False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise ValueError("downloaded class icon is not a valid PNG")
        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError("downloaded class icon has an invalid PNG checksum")
        if chunk_type == b"IHDR":
            if dimensions is not None or length != 13:
                raise ValueError("downloaded class icon is not a valid PNG")
            dimensions = struct.unpack(">II", chunk_data[:8])
        if chunk_type == b"IEND":
            saw_iend = True
            if length != 0:
                raise ValueError("downloaded class icon is not a valid PNG")
            break
        offset = chunk_end
    if dimensions is None or not saw_iend:
        raise ValueError("downloaded class icon is not a valid PNG")
    width, height = dimensions
    if (width, height) != expected_size:
        raise ValueError(
            f"downloaded class icon is {width}x{height}; expected "
            f"{expected_size[0]}x{expected_size[1]}"
        )


def vendor_icons(target: Path, *, timeout_seconds: float = 30) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for filename in CLASS_ICON_FILES:
        request = Request(
            f"{SOURCE_ROOT}/{filename}",
            headers={"User-Agent": "wow-forever-home-assistant-build/1.13.0"},
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            data = response.read()
        validate_png(data)
        destination = target / filename
        temporary = destination.with_suffix(".png.tmp")
        temporary.write_bytes(data)
        temporary.replace(destination)
        print(f"Vendored {filename} ({len(data)} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=30)
    args = parser.parse_args()
    vendor_icons(args.target, timeout_seconds=args.timeout_seconds)


if __name__ == "__main__":
    main()
