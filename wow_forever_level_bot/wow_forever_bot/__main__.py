from __future__ import annotations

import asyncio
import logging
import os

from .bot import run_bot
from .config import Settings


def main() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_bot(Settings.from_env()))


if __name__ == "__main__":
    main()
