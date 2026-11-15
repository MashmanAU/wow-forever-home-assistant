import asyncio

import pytest

from wow_forever_bot.blizzard import BlizzardAPIError, BlizzardClient


def test_invalid_region_is_rejected_without_network() -> None:
    async def scenario() -> None:
        client = BlizzardClient("id", "secret")
        with pytest.raises(BlizzardAPIError, match="Region"):
            await client.get_character("First", "Surname", "moon")

    asyncio.run(scenario())
