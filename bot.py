from __future__ import annotations

import discord, logging, platform, traceback, wavelink
from aiohttp import ClientSession
from asqlite import Pool
from discord import Intents, Activity, ActivityType, Embed, app_commands, utils
from discord.ext.commands import Bot, when_mentioned_or, errors
from typing import List

from settings import DEFAULT_PREFIX, ACTIVITY_NAME, DEBUG_WEBHOOK

class Furina(Bot):
    """
    Customized `commands.Bot` class

    Attributes
    -----------
    - pool: `asqlite.Pool`
        - The database pool for the bot for easier database access
    - client_session: `aiohttp.ClientSession`
        - The client session for the bot for easier http request

    Example
    -----------
    .. code-block:: python
        async with aiohttp.ClientSession() as client_session, asqlite.create_pool("config.db") as pool:
            async with Furina(pool=pool, client_session=client_session) as bot:
                await bot.start(TOKEN)
    """
    def __init__(self, *, pool: Pool, client_session: ClientSession) -> None:
        super().__init__(
            command_prefix     = self.get_pre,
            case_insensitive   = True,
            strip_after_prefix = True,
            intents            = Intents.all(),
            help_command       = None,
            allowed_contexts   = app_commands.AppCommandContext(dm_channel=False, guild=True),
            activity           = Activity(type=ActivityType.playing,
                                          name=ACTIVITY_NAME,
                                          state="Playing: N̸o̸t̸h̸i̸n̸g̸")
        )
        self.pool = pool
        self.cs = client_session

    async def create_prefix_table(self) -> None:
        """Create a `custom_prefixes` table in the database"""
        async with self.pool.acquire() as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS custom_prefixes
                   ( guild_id INT NOT NULL PRIMARY KEY, prefix TEXT NOT NULL )""")
            
    async def update_prefixes(self) -> None:
        """Retrieve all prefixes in the `custom_prefixes` table and cache them in `Furina.prefixes`"""
        async with self.pool.acquire() as db:
            async with db.execute("""SELECT * FROM custom_prefixes""") as cursor:
                prefixes = await cursor.fetchall()
                self.prefixes = {prefix[0]: prefix[1] for prefix in prefixes}
            
    def get_pre(self, _, message: discord.Message) -> List[str]:
        """Custom `get_prefix` method"""
        prefix = self.prefixes.get(message.guild.id) or DEFAULT_PREFIX
        return when_mentioned_or(prefix)(self, message)

    async def on_ready(self) -> None:
        logging.info(f"Logged in as {self.user.name}")
        logging.info(f"discord.py v{discord.__version__}")
        logging.info(f"Wavelink v{wavelink.__version__}")
        logging.info(f"Running Python {platform.python_version()}")

        try:
            embed = Embed(color=self.user.accent_color).set_author(
                name="BOT IS READY!",
                icon_url=self.user.display_avatar.url
            )
            embed.timestamp = utils.utcnow()
            discord.SyncWebhook.from_url(DEBUG_WEBHOOK).send(embed=embed)
        except ValueError:
            logging.warning("Cannot get the Webhook url for on_ready events."
                            "If you don't want to get a webhook message when the bot is ready, please ignore this")

    async def setup_hook(self) -> None:
        await self.create_prefix_table()
        await self.update_prefixes()

        # loads the extensions
        from _extensions import EXTENSIONS
        for extension in EXTENSIONS:
            try:
                await self.load_extension(f"{extension}")
                logging.info(f"Loaded extension: {extension}")
            except errors.NoEntryPointError:
                logging.error(f"Extension {extension} has no setup function so it cannot be loaded")
            except Exception as e:
                traceback.print_exc()
                logging.error(f"An error occured when trying to load {extension}\n{e}")
        await self.load_extension("jishaku")
        logging.info("Loaded Jishaku extension")

