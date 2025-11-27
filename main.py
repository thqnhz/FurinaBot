"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

import asyncio
import sys

from aiohttp import ClientSession

from core import FurinaBot, settings, utils


async def main() -> None:
    """Setting up loggings and starting the bot."""
    utils.setup_logging()
    async with (
        ClientSession() as client_session,
        FurinaBot(client_session=client_session) as bot,
    ):
        await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
