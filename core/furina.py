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
import logging
import typing
from collections import defaultdict
from pathlib import Path
from platform import python_version

import asqlite
import discord
import lavalink
from discord import app_commands, ui, utils
from discord.ext import commands
from discord.ext.commands import errors, when_mentioned_or

from cogs import EXTENSIONS
from core import settings
from core.sql import SQL
from core.views import Container, LayoutView

if typing.TYPE_CHECKING:
    from datetime import datetime

    import aiohttp


class FurinaCtx(commands.Context):
    """Custom Context class with some shortcuts"""

    bot: FurinaBot

    async def tick(self) -> None:
        """React checkmark to the command message"""
        try:
            await self.message.add_reaction(settings.CHECKMARK)
        except discord.HTTPException:
            pass

    async def cross(self) -> None:
        """React a cross to the command message"""
        try:
            await self.message.add_reaction(settings.CROSS)
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
    r"""Customized :class:`commands.Bot` class

    Attributes
    ----------
    client_session : :class:`aiohttp.ClientSession`
        Aiohttp client session for making requests
    skip_lavalink : :class:`bool`
        Whether to skip Lavalink or not

    Usage
    -----
    .. code-block:: python
        async with aiohttp.ClientSession() as client_session, \
            FurinaBot(
                client_session=client_session,
                skip_lavalink=True
            ) as bot:
                await bot.start()
    """

    DEFAULT_PREFIX: str = settings.DEFAULT_PREFIX

    def __init__(
        self, *, client_session: aiohttp.ClientSession, skip_lavalink: bool
    ) -> None:
        super().__init__(
            command_prefix=self.get_pre,
            case_insensitive=True,
            strip_after_prefix=True,
            intents=discord.Intents(
                guilds=True,
                members=True,
                voice_states=True,
                messages=True,
                message_content=True,
            ),
            allowed_contexts=app_commands.AppCommandContext(
                dm_channel=False, guild=True
            ),
            allowed_mentions=discord.AllowedMentions.none(),
            activity=discord.Activity(
                type=discord.ActivityType.playing, name=settings.ACTIVITY_NAME
            ),
        )
        self.owner_id = settings.OWNER_ID
        self.skip_lavalink = skip_lavalink
        self._lavalink = None
        self.cs = client_session
        # custom prefixes, in `{guild_id: prefix}` format
        self.prefixes: dict[int, str] = {}
        self.command_cache = defaultdict(list)
        self.app_command_cache = defaultdict(list)

    @property
    def embed(self) -> discord.Embed:
        """Embed with default footer"""
        return discord.Embed().set_footer(text="Coded by ThanhZ")

    @property
    def uptime(self) -> str:
        """The bot uptime, formatted as `Xd Yh Zm`"""
        uptime_td = utils.utcnow() - self._startup
        return (
            f"`{uptime_td.days}d {uptime_td.seconds // 3600}h"
            f" {(uptime_td.seconds // 60) % 60}m`"
        )

    @property
    def lavalink(self) -> lavalink.Client:
        if not self._lavalink:
            self._lavalink = lavalink.Client(self.user.id)
            self._lavalink.add_node(
                host=settings.LAVA_URL,
                region="us",
                port=1710,
                password=settings.LAVA_PW,
            )
        return self._lavalink

    async def get_context(
        self,
        message: discord.Message,
        *,
        cls: FurinaCtx = FurinaCtx,  # type: ignore[reportArgumentType]
    ) -> FurinaCtx:
        return await super().get_context(message, cls=cls)  # type: ignore[reportArgumentType]

    def get_pre(self, _: FurinaBot, message: discord.Message) -> list[str]:
        """Custom `get_prefix` method

        Parameters
        ----------
        _ : :class:`FurinaBot`
            The bot instance,
            but since this is a method in the bot class,
            we already have `self` as bot
        message : :class:`discord.Message`
            The message to get the prefix

        Returns
        -------
        :class:`list[str]`
            The prefix for the bot, including mention
        """
        if not message.guild:
            return when_mentioned_or(self.DEFAULT_PREFIX)(self, message)
        prefix = self.prefixes.get(message.guild.id) or self.DEFAULT_PREFIX
        return when_mentioned_or(prefix)(self, message)

    async def on_ready(self) -> None:
        self.user: discord.ClientUser
        logging.info("Logged in as %s", self.user.name)
        await self.pool.executemany(
            """INSERT OR REPLACE INTO guilds (id) VALUES (?)""",
            [(guild.id,) for guild in self.guilds],
        )
        self._startup: datetime = utils.utcnow()
        view = LayoutView(Container(ui.TextDisplay("### BOT IS READY!")))
        webhook = discord.Webhook.from_url(settings.DEBUG_WEBHOOK, client=self)
        message = await webhook.send(
            view=view,
            avatar_url=self.user.display_avatar.url,
            username=self.user.display_name,
            silent=True,
            wait=True,
        )
        await asyncio.sleep(10)
        await message.delete()

    async def setup_hook(self) -> None:
        logging.info("discord.py v%s", discord.__version__)
        logging.info("Lavalink.py v%s", lavalink.__version__)
        logging.info("Running Python %s", python_version())
        logging.info("Fetching bot emojis...")
        self.app_emojis = await self.fetch_application_emojis()
        db_path = Path() / "db"
        db_path.mkdir(exist_ok=True)
        self.pool = SQL(await asqlite.create_pool(Path() / "db" / "furina.db"))  # type: ignore[reportArgumentType]
        await self.pool.create_tables()
        await self.__load_extensions()

    async def __load_extensions(self) -> None:
        """Load bot extensions"""
        logging.info("Loading extensions...")
        for extension in EXTENSIONS:
            extension_name = extension[5:]
            try:
                await self.load_extension(extension)
            except errors.NoEntryPointError:
                logging.exception(
                    "Extension %s has no setup function so it cannot be loaded",
                    extension_name,
                )
            except Exception:
                logging.exception(
                    "An error occured when trying to load %s", extension_name
                )

    async def start(self) -> None:
        await super().start(settings.TOKEN)


class FurinaCog(commands.Cog):
    """Base class for all cogs"""

    def __init__(self, bot: FurinaBot) -> None:
        self.bot = bot
        self.pool: SQL = bot.pool
        self.cs = bot.cs

    async def cog_load(self) -> None:
        logging.info("Cog %s has been loaded", self.__cog_name__)

    @property
    def embed(self) -> discord.Embed:
        """Shortcut for `FurinaBot.embed`"""
        return self.bot.embed
