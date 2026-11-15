from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from .commentary import CommentaryService
from .daily import build_fixture_daily_bundle, progress_summary_lines
from .test_environment import SCENARIOS


def _markdown(bundle) -> str:
    lines = [
        "# WoW Forever synthetic daily preview",
        "",
        "> TEST DATA ONLY — no live database or Discord schedule was read or changed.",
        "",
        f"**Scenario:** `{bundle.scenario}`  ",
        f"**Commentary source:** `{bundle.commentary.source}`  ",
        f"**Primary story angle:** `{bundle.commentary.story_angle}`",
        "",
        "## Radio intro",
        "",
        bundle.commentary.text,
        "",
        "## Verified synthetic progress",
        "",
    ]
    lines.extend(f"- {line}" for line in progress_summary_lines(bundle.progress))
    lines.extend(["", "## Synthetic Wowhead headlines", ""])
    lines.extend(f"- [{item.title}]({item.url})" for item in bundle.news)
    lines.append("")
    return "\n".join(lines)


async def _run(args: argparse.Namespace) -> int:
    commentary = CommentaryService(
        os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        max_words=args.max_words,
        roast_level=args.roast_level,
    )
    try:
        bundle = await build_fixture_daily_bundle(
            commentary,
            scenario=args.scenario,
            root=args.test_root,
        )
    finally:
        await commentary.close()

    output = _markdown(bundle)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(output, encoding="utf-8")
        print(target)
    else:
        print(output)
    if args.payload:
        payload_target = Path(args.payload)
        payload_target.parent.mkdir(parents=True, exist_ok=True)
        payload_target.write_text(
            json.dumps(bundle.payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        print(payload_target)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic WoW Forever preview without Discord or the live database."
    )
    parser.add_argument("--scenario", choices=SCENARIOS, default="radio-day")
    parser.add_argument("--roast-level", choices=("gentle", "mild", "spicy"), default="mild")
    parser.add_argument("--max-words", type=int, default=70)
    parser.add_argument("--test-root", default="/tmp/wow_forever_preview_cli")
    parser.add_argument("--output", help="Optional Markdown output path")
    parser.add_argument("--payload", help="Optional controlled JSON payload output path")
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
