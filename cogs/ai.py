from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands
from deep_translator import GoogleTranslator, MyMemoryTranslator

from furina import FurinaCtx, FurinaCog


if TYPE_CHECKING:
    from furina import FurinaBot


class AI(FurinaCog):
    """AI Related Commands"""
    @commands.hybrid_command(name="translate", aliases=['tr'], description="Translate using Google Translate and MyMemory")
    async def translate_command(self, ctx: FurinaCtx, *, text: str) -> None:
        """
        Translate using Google Translate and MyMemory

        Parameters
        -----------
        text
            - A string that need to be translated
        """
        await ctx.tick()
        msg = await ctx.reply(embed=ctx.embed.set_author(name="Translating..."))
        google_translator = GoogleTranslator().translate(text)
        mymemory_translator = MyMemoryTranslator().translate(text)
        embed = ctx.embed
        embed.title = "Translate"
        embed.add_field(name="Original", value=text)
        embed.add_field(name="Google Translate", value=google_translator[:1000], inline=False)
        embed.add_field(name="MyMemory Translate", value=mymemory_translator[:1000], inline=False)
        await msg.edit(embed=embed)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(AI(bot))
