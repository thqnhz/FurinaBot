from __future__ import annotations

import logging
import traceback
from aiohttp import ClientSession
from platform import python_version
from typing import List


import discord
import wavelink
from asyncpg import Pool
from discord import app_commands, utils, Activity, ActivityType, Embed, Intents
from discord.ext.commands import errors, Bot, Context, when_mentioned_or


from settings import DEFAULT_PREFIX, ACTIVITY_NAME, DEBUG_WEBHOOK, CHECKMARK


class FurinaCtx(Context):
    async def tick(self) -> None:
        """Reacts checkmark to the command message"""
        try:
            await self.message.add_reaction(CHECKMARK)
        except discord.HTTPException:
            pass
    
    @property
    def pool(self) -> Pool:
        """Shortcut for `FurinaBot.pool`"""
        return self.bot.pool
    
    @property
    def cs(self) -> ClientSession:
        """Shortcut for `FurinaBot.cs`"""
        return self.bot.cs
    
    @property
    def embed(self) -> Embed:
        """Shortcut for FurinaBot.embed"""
        return self.bot.embed
    

class FurinaBot(Bot):
    """
    Customized `commands.Bot` class

    Attributes
    -----------
    - pool: `asyncpg.Pool`
        - The database pool for the bot for easier database access
    - client_session: `aiohttp.ClientSession`
        - The client session for the bot for easier http request

    Example
    -----------
    .. code-block:: python
        async with aiohttp.ClientSession() as client_session, asynpg.create_pool("config.db") as pool:
            async with FurinaBot(pool=pool, client_session=client_session) as bot:
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

    @property
    def embed(self):
        return Embed().set_footer(text="Coded by ThanhZ")
    
    async def get_context(self, message: discord.Message, *, cls = FurinaCtx):
        return await super().get_context(message, cls=cls)

    async def create_prefix_table(self) -> None:
        """Create a `custom_prefixes` table in the database"""
        async with self.pool.acquire() as con:
            await con.execute(
                """CREATE TABLE IF NOT EXISTS custom_prefixes
                   (
                        guild_id BIGINT NOT NULL PRIMARY KEY,
                        prefix TEXT NOT NULL
                   );""")
            
    async def update_prefixes(self) -> None:
        """Retrieve all prefixes in the `custom_prefixes` table and cache them in `Furina.prefixes`"""
        async with self.pool.acquire() as con:
            prefixes = await con.fetch("""SELECT * FROM custom_prefixes""")
            self.prefixes = {prefix["guild_id"]: prefix["prefix"] for prefix in prefixes}
            
    def get_pre(self, _, message: discord.Message) -> List[str]:
        """Custom `get_prefix` method"""
        prefix = self.prefixes.get(message.guild.id) or DEFAULT_PREFIX
        return when_mentioned_or(prefix)(self, message)

    async def on_ready(self) -> None:
        logging.info(f"Logged in as {self.user.name}")

        try:
            embed = self.embed.set_author(name="BOT IS READY!")
            embed.color = self.user.accent_color
            embed.timestamp = utils.utcnow()
            webhook = discord.Webhook.from_url(DEBUG_WEBHOOK, client=self)
            await webhook.send(embed=embed, avatar_url=self.user.display_avatar.url, username=self.user.display_name)
        except ValueError:
            logging.warning("Cannot get the Webhook url for on_ready events."
                            "If you don't want to get a webhook message when the bot is ready, please ignore this")

    async def setup_hook(self) -> None:
        logging.info(f"discord.py v{discord.__version__}")
        logging.info(f"Wavelink v{wavelink.__version__}")
        logging.info(f"Running Python {python_version()}")
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


