from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

import enka

if TYPE_CHECKING:
    from bot import FurinaBot


class Gacha(commands.Cog):
    """Genshin Related Commands"""
    def __init__(self, bot: FurinaBot):
        self.bot = bot
        self.gi = enka.GenshinClient()
        self.hsr = enka.HSRClient()

    @commands.command(name='gi', description="Get user info")
    async def enka_gi(self, ctx: commands.Context, uid: str):
        async with self.gi as api:
            response = await api.fetch_showcase(uid)
            player_info = response.player
        embed = self.bot.embed
        embed.title = f"{player_info.nickname}"
        embed.set_author(name=uid, icon_url=player_info.profile_picture_icon.circle)
        embed.set_thumbnail(url=player_info.namecard.full)
        embed.description = (f"> {player_info.signature}\n"
                                f"**Adventure Rank:** `{player_info.level}`\n"
                                f"**World Level:** `{player_info.world_level}`\n"
                                f"**Achievements:** `{player_info.achievements}`\n"
                                f"**Abyss Floor:** `{player_info.abyss_floor}-{player_info.abyss_level} ({player_info.abyss_stars})`"
        )
        embed.set_footer(text="Coded by ThanhZ | Powered by Enka Network")
        await ctx.reply(embed=embed)

    @commands.command(name='hsr')
    async def enka_hsr(self, ctx: commands.Context, uid: str):
        async with self.hsr as api:
            response = await api.fetch_showcase(uid)
            player_info = response.player
            player_stats = player_info.stats
        embed = self.bot.embed
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


async def setup(bot: FurinaBot):
    await bot.add_cog(Gacha(bot))