from __future__ import annotations
import aiohttp, asqlite, asyncio, discord, logging, os

from bot import Furina
from settings import TOKEN

os.makedirs("logs", exist_ok=True)

log_handler = logging.FileHandler(filename="logs/furina.log")
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

async def main():
    discord.utils.setup_logging(handler=log_handler)
    async with aiohttp.ClientSession() as client_session, asqlite.create_pool("config.db") as pool:
        async with Furina(pool=pool, client_session=client_session) as bot:
            await bot.start(TOKEN)

asyncio.run(main())
