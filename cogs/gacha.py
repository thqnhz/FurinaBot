from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import asqlite
import discord
import enka
from discord.ext import commands

from furina import FurinaCog, FurinaCtx


if TYPE_CHECKING:
    from furina import FurinaBot


class Gacha(FurinaCog):
    """Gacha Related Commands"""
    def __init__(self, bot: FurinaBot):
        super().__init__(bot)
        self.gi = enka.GenshinClient()
        self.hsr = enka.HSRClient()

    async def cog_load(self) -> None:
        self.pool = await asqlite.create_pool(pathlib.Path() / 'db' / 'gacha.db')
        await self.__create_gacha_tables()
        return await super().cog_load()
    
    async def __create_gacha_tables(self) -> None:
        async with self.pool.acquire() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS gi_uid
                (
                    user_id INTEGER NOT NULL PRIMARY KEY,
                    uid TEXT NOT NULL
                )
                """)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS hsr_uid
                (
                    user_id INTEGER NOT NULL PRIMARY KEY,
                    uid TEXT NOT NULL
                )
                """)

    @property
    def embed(self) -> discord.Embed:
        """Shortcut for FurinaBot.embed"""
        return self.bot.embed.set_footer(text="Coded by ThanhZ | Powered by Enka Network")

    @commands.hybrid_group(name='gi', description="Get user info", fallback='get')
    async def gi_group(self, ctx: FurinaCtx, uid: str = None):
        if uid is None:
            async with self.pool.acquire() as db:
                uid = await db.fetchone("SELECT uid FROM gi_uid WHERE user_id = ?", ctx.author.id)
                uid = uid[0] if uid else None
                if uid is None:
                    return await ctx.reply("You have not set a UID yet! Use `/gi set <uid>` to set your UID")
                
        async with self.gi as api:
            response = await api.fetch_showcase(uid)
            player_info = response.player
        embed = self.embed
        embed.title = f"{player_info.nickname}"
        embed.set_author(name=uid, icon_url=player_info.profile_picture_icon.circle)
        embed.set_thumbnail(url=player_info.namecard.full)
        embed.description = (f"> {player_info.signature}\n"
                             f"**Adventure Rank:** `{player_info.level}`\n"
                             f"**World Level:** `{player_info.world_level}`\n"
                             f"**Achievements:** `{player_info.achievements}`\n"
                             f"**Abyss Floor:** `{player_info.abyss_floor}-{player_info.abyss_level} ({player_info.abyss_stars})`"
        )
        await ctx.reply(embed=embed)

    @gi_group.command(name='set', description='Set your UID')
    async def set_uid_gi(self, ctx: FurinaCtx, *, uid: str):
        async with self.gi as api, self.pool.acquire() as db:
            try:
                await api.fetch_showcase(uid, info_only=True)
            except enka.errors.WrongUIDFormatError:
                return await ctx.reply("Invalid UID!")
            await db.execute("INSERT OR REPLACE INTO gi_uid (user_id, uid) VALUES (?, ?)", ctx.author.id, uid)
        await ctx.reply("Your GI UID has been set to: " + uid)

    @commands.hybrid_group(name='hsr', description="Get HSR user info", fallback='get')
    async def hsr_group(self, ctx: FurinaCtx, uid: str = None):
        if not uid:
            async with self.pool.acquire() as db:
                uid = await db.fetchone("SELECT uid FROM hsr_uid WHERE user_id = ?", ctx.author.id)
                uid = uid[0] if uid else None
                if uid is None:
                    return await ctx.reply("You have not set a UID yet! Use `/hsr set <uid>` to set your UID")
                
        async with self.hsr as api:
            response = await api.fetch_showcase(uid)
            player_info = response.player
            player_stats = player_info.stats
        embed = self.embed
        embed.title = f"{player_info.nickname}"
        embed.set_author(name=uid, icon_url=player_info.icon)
        embed.description = (f"> {player_info.signature}\n"
                             f"**Trailblaze Level:** `{player_info.level}`\n"
                             f"**Equilibrium Level:** `{player_info.equilibrium_level}`\n"
                             f"**Stats:**\n"
                             f">>> **Achievements**: `{player_stats.achievement_count}`\n"
                             f"**Characters**: `{player_stats.character_count}`\n"
                             f"**Lightcones**: `{player_stats.light_cone_count}`"
        )
        embed.set_footer(text="Coded by ThanhZ | Powered by Enka Network")
        await ctx.reply(embed=embed)

    @hsr_group.command(name='set', description='Set your UID')
    async def set_uid_hsr(self, ctx: FurinaCtx, *, uid: str):
        async with self.hsr as api, self.pool.acquire() as db:
            try:
                await api.fetch_showcase(uid, info_only=True)
            except enka.errors.WrongUIDFormatError:
                return await ctx.reply("Invalid UID!")
            await db.execute("INSERT OR REPLACE INTO hsr_uid (user_id, uid) VALUES (?, ?)", ctx.author.id, uid)
        await ctx.reply("Your HSR UID has been set to: " + uid)


async def setup(bot: FurinaBot):
    await bot.add_cog(Gacha(bot))