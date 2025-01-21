from __future__ import annotations

from discord.ext import commands
from deep_translator import GoogleTranslator, MyMemoryTranslator
from typing import TYPE_CHECKING

from _classes.embeds import LoadingEmbed, FooterEmbed

if TYPE_CHECKING:
    from bot import Furina


class AI(commands.Cog):
    """AI Related Commands"""
    def __init__(self, bot: Furina) -> None:
        self.bot = bot

    @commands.hybrid_command(name="translate", aliases=['tr'], description="Translate using Google Translate and MyMemory")
    async def translate_command(self, ctx: commands.Context, *, text: str) -> None:
        """
        Translate using Google Translate and MyMemory

        Parameters
        -----------
        ctx
            `commands.Context`
        text
            A string that need to be translated
        """
        msg = await ctx.reply(embed=LoadingEmbed("Translating..."))
        google_translator = GoogleTranslator(source="auto", target="vi").translate(text)
        mymemory_translator = MyMemoryTranslator(source="en-US", target="vi-VN").translate(text)
        embed = FooterEmbed(title="Translate", description=f"**Original:** {text}")
        embed.add_field(name="Google Translate", value=google_translator)
        embed.add_field(name="MyMemory Translate", value=mymemory_translator, inline=False)
        await msg.edit(embed=embed)


async def setup(bot: Furina):
    await bot.add_cog(AI(bot))
