from __future__ import annotations
import aiohttp, asqlite, asyncio, discord
from keep_alive import keep_alive

from bot import Furina
from settings import TOKEN

async def main():
    discord.utils.setup_logging()
    async with aiohttp.ClientSession() as client_session, asqlite.create_pool("config.db") as pool:
        async with Furina(pool=pool, client_session=client_session) as bot:
            keep_alive()
            await bot.start(TOKEN)

asyncio.run(main())
