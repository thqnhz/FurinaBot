from __future__ import annotations

from typing import TYPE_CHECKING

import asqlite
from discord.ext import commands

from furina import FurinaCog, FurinaCtx


if TYPE_CHECKING:
    from furina import FurinaBot


class Economy(FurinaCog):
    """Economy Related Commands"""
    def __init__(self, bot):
        super().__init__(bot)
        self.pool: asqlite.Pool = asqlite.create_pool('furina.db')

    # async def cog_load(self):
    #     await self.__update_economy_emojis()
    #     await self.__create_economy_tables()
    #     return await super().cog_load()
    
    async def __update_economy_emojis(self):
        emojis = await self.bot.fetch_application_emojis()
        for emoji in emojis:
            if emoji.name == 'primogem':
                self.primo = f"<{emoji.name}:{emoji.id}>"
                break
        if not self.primo:
            with open('./assets/economy/primogem.png', 'r') as primo:
                image = primo.read()
                emoji = await self.bot.create_application_emoji(name='primogem',image=image)
                self.primo = f"<{emoji.name}:{emoji.id}>"

    async def __create_economy_tables(self):
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
                """)

    @commands.command(name='daily')
    async def eco_daily(self, ctx: FurinaCtx):
        raise NotImplemented


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Economy(bot))