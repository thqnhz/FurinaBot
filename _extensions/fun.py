import discord
from discord.ext import commands

from _classes.embeds import *
from helper import random_lag_emote


class Fun(commands.Cog):
    """Lệnh funny hahaha XD."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        msg = message.content.lower()
        if any(_ in msg for _ in ["viettel", "vietteo", "vitteo", "mạng 7 chữ",
                                  "vnpt", "vienpiti", "vê en pê tê",
                                  "mạng 4 chữ", "fpt", "ép pê tê", "mạng 3 chữ"]):
            lag: str = random_lag_emote()
            await message.channel.send(lag)
            return

        if any(_ in msg for _ in ["doan tom", "tôm", "đoàn tân", "tân"]):
            await message.channel.send(
                """# <@889183721389953115> lolicon + đuôi + mù + điếc + fan MU + đáy xã hội + vấn đề kĩ năng""",
                silent=True
            )
            return

        if "nowaying" in msg:
            await message.channel.send("https://cdn.7tv.app/emote/63c8a6c330027778647b3de8/3x.gif")
            return

        if "aintnoway" in msg:
            await message.channel.send("https://cdn.7tv.app/emote/6329da94345c8855a28db877/3x.gif")
            return

        if any(_ in msg for _ in ["skill issue", "skillissue",
                                  "van de ky nang", "van de ki nang",
                                  "vấn đề kĩ năng", "vấn đề kỹ năng"]):
            await message.channel.send("https://cdn.7tv.app/emote/63d806d6f3396825289f86b4/3x.webp")

    @commands.command(name='botngu',
                      aliases=['ngu'],
                      description="Bot ngu quãi lều.")
    async def botngu(self, ctx: commands.Context) -> None:
        embed = ImageEmbed(
            title="Sao bạn lại chửi mình ngu :sob:",
            desc=f"<@596886610214125598> ơi {ctx.author.mention} chửi bé là ngu.",
            image="https://media1.tenor.com/m/2ROZqn-Kr1IAAAAd/furina-furina-cry.gif"
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))

