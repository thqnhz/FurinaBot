from __future__ import annotations

import random
from typing import TYPE_CHECKING

from discord import app_commands, Interaction, Message
from discord.ext import commands

from settings import GUILD_SPECIFIC


if TYPE_CHECKING:
    from bot import FurinaBot


class Fun(commands.Cog):
    """Funni Commands haha XD"""
    def __init__(self, bot: FurinaBot) -> None:
        self.bot = bot
        self.ctx_menu_liemeter = app_commands.ContextMenu(name="Lie Detector", callback=self.lie_detector)
        self.bot.tree.add_command(self.ctx_menu_liemeter)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu_liemeter.name, type=self.ctx_menu_liemeter.type)

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot:
            return
        
        if message.guild != GUILD_SPECIFIC:
            return
        
        msg = message.content.lower()
        if any(_ in msg for _ in ["viettel", "vietteo", "vitteo", "mạng 7 chữ",
                                  "vnpt", "vienpiti", "vê en pê tê",
                                  "mạng 4 chữ", "fpt", "ép pê tê", "mạng 3 chữ"]):
            lag: str = self._random_lag_emote()
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

    @staticmethod
    def _random_lag_emote() -> str:
        emote = random.choice([
            'https://cdn.7tv.app/emote/60ae9173f39a7552b68f9730/4x.gif',
            'https://cdn.7tv.app/emote/63c9080bec685e58d1727476/4x.gif',
            'https://cdn.7tv.app/emote/60afcde452a13d1adba73d29/4x.gif',
            'https://cdn.7tv.app/emote/62fd78283b5817bb65704cb6/4x.gif',
            'https://cdn.7tv.app/emote/616ecf20ffc7244d797c6ef8/4x.gif',
            'https://cdn.7tv.app/emote/6121af3d5277086f91cd6f03/4x.gif',
            'https://cdn.7tv.app/emote/61ab007b15b3ff4a5bb954f4/4x.gif',
            'https://cdn.7tv.app/emote/64139e886b843cb8a7001681/4x.gif',
            'https://cdn.7tv.app/emote/64dacca4bd944cda3ad5971f/4x.gif',
            'https://cdn.7tv.app/emote/62ff9b877de1b22af65895d7/4x.webp',
            'https://cdn.7tv.app/emote/646748346989b9b0d46adc50/4x.webp'
        ])
        return emote
    
    async def lie_detector(self, interaction: Interaction, message: Message):
        await interaction.response.send_message("Verifying message...", delete_after=5)
        if random.random() < 0.5:
            await message.channel.send("This message is verified to be the truth", reference=message)
        else:
            await message.channel.send("https://tenor.com/kXIbVjdMB8x.gif", reference=message)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Fun(bot))

