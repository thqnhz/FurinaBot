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

from typing import TYPE_CHECKING

import discord
import enka
from discord import ui
from discord.ext import commands

from core import FurinaCog, FurinaCtx
from core.views import Container, LayoutView

if TYPE_CHECKING:
    from core import FurinaBot


class NotFoundError(Exception):
    pass


class Gacha(FurinaCog):
    """Gacha Related Commands"""

    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)
        self.gi = enka.GenshinClient()
        self.hsr = enka.HSRClient()

    async def cog_load(self) -> None:
        await self.gi.start()
        await self.gi.update_assets()
        await self.hsr.start()
        await self.hsr.update_assets()
        await super().cog_load()

    @property
    def embed(self) -> discord.Embed:
        """Shortcut for `FurinaBot.embed`, with extra footer"""
        return self.bot.embed.set_footer(text="Coded by ThanhZ | Powered by Enka Network")

    async def set_uid(self, sql: str, user_id: int, uid: str) -> None:
        """Insert a user's UID with provided game to the database

        Parameters
        ----------
        sql : :class:`str`
            SQL query to execute
        user_id : :class:`int`
            Discord user ID
        uid : :class:`str`
            UID to set
        """
        await self.pool.execute(sql, user_id, uid)

    async def get_uid(self, sql: str, user_id: int) -> str:
        """Get a user's UID from the database

        Parameters
        ----------
        sql : :class:`str`
            SQL query to execute
        user_id : :class:`int`
            Discord user ID

        Returns
        -------
        str
            UID of the user

        Raises
        ------
        NotFoundError
            UID not found
        """
        return await self.pool.fetchval(sql, user_id)

    @commands.hybrid_group(name="gi", fallback="get")
    async def gi_group(self, ctx: FurinaCtx, uid: str | None = None) -> None:
        """Get Genshin Impact user info

        Get Genshin Impact user info by UID.
        If no UID is provided, the bot will try to get your UID.
        Use `/gi set <uid>` to set your UID.

        Parameters
        ----------
        uid : str, optional
            Genshin UID
        """
        if uid is None:
            uid = await self.get_uid("SELECT uid FROM gi_uid WHERE user_id = ?", ctx.author.id)

        async with self.gi as api:
            response = await api.fetch_showcase(uid)
            p_info = response.player
        abyss = f"{p_info.abyss_floor}-{p_info.abyss_level} ({p_info.abyss_stars})"

        container = Container(
            ui.MediaGallery(discord.MediaGalleryItem(p_info.namecard.full)),
            ui.Separator(),
            ui.Section(
                ui.TextDisplay(f"## {p_info.nickname} ({uid})"),
                ui.TextDisplay(
                    f"> {p_info.signature}\n"
                    f"**Adventure Rank:** `{p_info.level}` "
                    "▪ **World Level:** `{p_info.world_level}`\n"
                    f"**Achievements:** `{p_info.achievements}`\n"
                    f"**Abyss Floor:** `{abyss}`"
                ),
                accessory=ui.Thumbnail(p_info.profile_picture_icon.circle),
            ),
        ).add_footer()
        await ctx.reply(view=LayoutView(container))

    @gi_group.command(name="set")
    async def set_uid_gi(self, ctx: FurinaCtx, *, uid: str) -> None:
        """Set your Genshin Impact UID

        Set your Genshin Impact UID to be used in the `/gi get` command.

        Parameters
        ----------
        uid : str
            Your Genshin UID
        """
        async with self.gi as api:
            await api.fetch_showcase(uid, info_only=True)
        await self.set_uid(
            "INSERT OR REPLACE INTO gi_uid (user_id, uid) VALUES (?, ?)", ctx.author.id, uid
        )
        await ctx.reply("Your GI UID has been set to: " + uid)

    @commands.hybrid_group(name="hsr", fallback="get")
    async def hsr_group(self, ctx: FurinaCtx, uid: str | None = None) -> None:
        """Get HSR Impact user info

        Get HSR Impact user info by UID.
        If no UID is provided, the bot will try to get your UID.
        Use `/hsr set <uid>` to set your UID.

        Parameters
        ----------
        uid : str, optional
            HSR UID
        """
        if not uid:
            uid = await self.get_uid("SELECT uid FROM hsr_uid WHERE user_id = ?", ctx.author.id)

        async with self.hsr as api:
            response = await api.fetch_showcase(uid)
            p_info = response.player
            p_stats = p_info.stats
        embed = self.embed
        embed.title = f"{p_info.nickname}"
        embed.set_author(name=uid, icon_url=p_info.icon)
        embed.description = (
            f"> {p_info.signature}\n"
            f"**Trailblaze Level:** `{p_info.level}`\n"
            f"**Equilibrium Level:** `{p_info.equilibrium_level}`\n"
            f"**Stats:**\n"
            f">>> **Achievements**: `{p_stats.achievement_count}`\n"
            f"**Characters**: `{p_stats.character_count}`\n"
            f"**Lightcones**: `{p_stats.light_cone_count}`"
        )
        await ctx.reply(embed=embed)

    @hsr_group.command(name="set", description="Set your UID")
    async def set_uid_hsr(self, ctx: FurinaCtx, *, uid: str) -> None:
        """Set your HSR Impact UID

        Set your HSR UID to be used in the `/hsr get` command.

        Parameters
        ----------
        uid : str
            Your HSR UID
        """
        async with self.hsr as api:
            await api.fetch_showcase(uid, info_only=True)
        await self.set_uid(
            "INSERT OR REPLACE INTO hsr_uid (user_id, uid) VALUES (?, ?)", ctx.author.id, uid
        )
        await ctx.reply("Your HSR UID has been set to: " + uid)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Gacha(bot))
