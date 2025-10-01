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

from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
from discord.ext import commands

from core import FurinaCog, FurinaCtx

if TYPE_CHECKING:
    from core import FurinaBot


class Economy(FurinaCog):
    """Economy Related Commands"""

    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)

    async def __update_economy_emojis(self) -> None:
        emojis = await self.bot.fetch_application_emojis()
        for emoji in emojis:
            if emoji.name == "primogem":
                self.primo = f"<{emoji.name}:{emoji.id}>"
        if not self.primo:
            primo_path = Path("./assets/economy/primogem.png")
            async with aiofiles.open(primo_path, mode="rb") as primo:
                image = await primo.read()
            emoji = await self.bot.create_application_emoji(name="primogem", image=image)
            self.primo = f"<{emoji.name}:{emoji.id}>"

    async def __create_economy_tables(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                    CREATE TABLE IF NOT EXISTS economy
                    (
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        balance INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (guild_id, user_id)
                    )
                """
            )

    @commands.command(name="daily")
    async def eco_daily(self, ctx: FurinaCtx) -> None:
        raise NotImplementedError


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Economy(bot))
