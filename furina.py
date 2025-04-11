from __future__ import annotations

import logging
import traceback
import typing
from platform import python_version

import aiohttp
import discord
import wavelink
from discord import app_commands, utils
from discord.ext import commands
from discord.ext.commands import errors, when_mentioned_or

from settings import ACTIVITY_NAME, CHECKMARK, CROSS, DEBUG_WEBHOOK, DEFAULT_PREFIX


class FurinaCtx(commands.Context):
    """Custom Context class with some shortcuts"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bot: FurinaBot
        self.message: discord.Message
    
    async def tick(self) -> None:
        """Reacts checkmark to the command message"""
        try:
            await self.message.add_reaction(CHECKMARK)
        except discord.HTTPException:
            pass

    async def cross(self) -> None:
        """Reacts a cross to the command message"""
        try:
            await self.message.add_reaction(CROSS)
        except discord.HTTPException:
            pass
    
    @property
    def cs(self) -> aiohttp.ClientSession:
        """Shortcut for `FurinaBot.cs`"""
        return self.bot.cs
    
    @property
    def embed(self) -> discord.Embed:
        """Shortcut for FurinaBot.embed"""
        return self.bot.embed
    

class FurinaBot(commands.Bot):
    """
    Customized `commands.Bot` class

    Attributes
    -----------
    - client_session: `aiohttp.ClientSession`
        - The client session for the bot for easier http request

    Example
    -----------
    .. code-block:: python
        async with aiohttp.ClientSession() as client_session:
            async with FurinaBot(client_session=client_session) as bot:
                await bot.start(TOKEN)
    """
    def __init__(self, *, client_session: aiohttp.ClientSession, skip_lavalink: bool) -> None:
        super().__init__(
            command_prefix     = self.get_pre,
            case_insensitive   = True,
            strip_after_prefix = True,
            intents            = discord.Intents.all(),
            help_command       = None,
            allowed_contexts   = app_commands.AppCommandContext(dm_channel=False, guild=True),
            activity           = discord.Activity(type=discord.ActivityType.playing,
                                          name=ACTIVITY_NAME,
                                          state="Playing: N̸o̸t̸h̸i̸n̸g̸")
        )
        self.skip_lavalink = skip_lavalink
        self.cs = client_session
        self.prefixes: typing.Dict[int, str] = {}

    @property
    def embed(self) -> discord.Embed:
        return discord.Embed().set_footer(text="Coded by ThanhZ")
    
    async def get_context(self, message: discord.Message, *, cls = FurinaCtx) -> FurinaCtx:
        return await super().get_context(message, cls=cls)

    def get_pre(self, _, message: discord.Message) -> typing.List[str]:
        """Custom `get_prefix` method"""
        if not message.guild:
            return when_mentioned_or(DEFAULT_PREFIX)(self, message)
        prefix = self.prefixes.get(message.guild.id) or DEFAULT_PREFIX
        return when_mentioned_or(prefix)(self, message)

    async def on_ready(self) -> None:
        logging.info(f"Logged in as {self.user.name}")
        self.uptime = utils.utcnow()

        try:
            embed = self.embed.set_author(name="BOT IS READY!")
            embed.color = self.user.accent_color
            embed.timestamp = utils.utcnow()
            webhook = discord.Webhook.from_url(DEBUG_WEBHOOK, client=self)
            await webhook.send(embed=embed, 
                               avatar_url=self.user.display_avatar.url, 
                               username=self.user.display_name)
        except ValueError:
            logging.warning("Cannot get the Webhook url for on_ready events."
                            "If you don't want to get a webhook message when the bot is ready, please ignore this")

    async def setup_hook(self) -> None:
        logging.info(f"discord.py v{discord.__version__}")
        logging.info(f"Wavelink v{wavelink.__version__}")
        logging.info(f"Running Python {python_version()}")
        logging.info("Fetching bot emojis")
        self.app_emojis: typing.List[discord.Emoji] = await self.fetch_application_emojis()

        # loads the extensions
        from cogs import EXTENSIONS
        logging.info("Loading extensions")
        for extension in EXTENSIONS:
            extension_name = extension[5:]
            try:
                await self.load_extension(f"{extension}")
            except errors.NoEntryPointError:
                logging.error(f"Extension {extension_name} has no setup function so it cannot be loaded")
            except Exception as e:
                traceback.print_exc()
                logging.error(f"An error occured when trying to load {extension_name}\n{e}")
        await self.load_extension("jishaku")
        logging.info("Loaded Jishaku extension")
  

class FurinaCog(commands.Cog):
    """Base class for all cogs"""
    def __init__(self, bot: FurinaBot) -> None:
        self.bot = bot
        
    async def cog_load(self) -> None:
        logging.info(f"Cog {self.__cog_name__} has been loaded")

    @property
    def embed(self) -> discord.Embed:
        return self.bot.embed
