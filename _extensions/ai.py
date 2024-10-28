from discord.ext import commands
from deep_translator import GoogleTranslator, MyMemoryTranslator

from _classes.embeds import *


class AI(commands.Cog):
    """Lệnh liên quan đến AI"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="translate", aliases=['tr'], description="Dịch thuật sử dụng Google & MyMemory.")
    async def translate_command(self,
                                ctx: commands.Context,
                                *,
                                text: str):
        """
        Dịch thuật sử dụng Google Translate & MyMemory Translate

        Parameters
        -----------
        ctx
            commands.Context
        text
            Đoạn văn bản cần dịch
        """
        msg = await ctx.reply(embed=LoadingEmbed("Đang dịch..."))
        google_translator = GoogleTranslator(source="auto", target="vi").translate(text)
        mymemory_translator = MyMemoryTranslator(source="en-US", target="vi-VN").translate(text)
        embed = FooterEmbed(title="Dịch", description=f"**Gốc:** {text}")
        embed.add_field(name="Google Translate", value=google_translator)
        embed.add_field(name="MyMemory Translate", value=mymemory_translator, inline=False)
        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(AI(bot))
