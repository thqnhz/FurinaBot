from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

import numpy as np
from discord import app_commands, Color, Interaction, Message
from discord.ext import commands

from furina import FurinaCog, FurinaCtx

if TYPE_CHECKING:
    from furina import FurinaBot


class Fun(FurinaCog):
    """Funni Commands haha XD"""
    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)
        self.ctx_menu_liemeter = app_commands.ContextMenu(name="Lie Detector", callback=self.lie_detector)
        self.bot.tree.add_command(self.ctx_menu_liemeter)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu_liemeter.name, type=self.ctx_menu_liemeter.type)
    
    async def lie_detector(self, interaction: Interaction, message: Message):
        if np.random.random() < 0.5:
            await interaction.response.send_message("This message is verified to be the truth")
        else:
            await interaction.response.send_message("https://tenor.com/kXIbVjdMB8x.gif")

    @staticmethod
    def generate_random_number(min_num: int, max_num: int, number: int = 1) -> List[int]:
        return np.random.randint(min_num, max_num + 1, 100*number).tolist()

    @commands.command(name='fortune', aliases=['lucky', 'slip', 'fortuneslip'], description="Draw a fortune slip")
    async def fortune_slip(self, ctx: FurinaCtx, number: Optional[int] = 1) -> None:
        misfortune = { "name": "Misfortune", "color": Color.darker_gray() }
        risingfortune = { "name": "Rising Fortune", "color": Color.dark_purple() }
        fortune = { "name": "Fortune", "color": Color.pink() }
        grandfortune = { "name": "Grand Fortune", "color": Color.red() }
        fortunes = [misfortune]*4 + [risingfortune]*3 + [fortune] * 2 + [grandfortune]
        embed = self.bot.embed
        if number == 1 or number not in range(1, 10_000):
            rand_num = self.generate_random_number(0, 9)[-1]
            embed.set_author(name=f"{ctx.author.display_name} thought very hard before drawing a fortune slip",
                            icon_url="https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif")
        else:
            rand_num = self.generate_random_number(0, 9, number)[-1]
            embed.set_author(name=f"{ctx.author.display_name} thought {number} times before drawing a fortune slip",
                            icon_url="https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif")
        embed.color = fortunes[rand_num]["color"]
        embed.title = fortunes[rand_num]["name"]
        await ctx.send(embed=embed)

    @commands.command(name='dice', aliases=['roll'], description="Roll a dice 6")
    async def dice(self, ctx: FurinaCtx, number: Optional[int] = 1) -> None:
        embed = self.bot.embed
        if number == 1 or number not in range(1, 1000):
            rand_num = self.generate_random_number(1, 6)[-1]
            embed.set_author(name=f"{ctx.author.display_name} rolled a dice",
                            icon_url="https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif")
        else:
            seq = self.generate_random_number(1, 6, number)
            seq = [str(seq_) for seq_ in seq]
            rand_num = seq[-1]
            embed.add_field(name="History:", value=f"```\n{' '.join(seq[:500]) + ('...' if len(seq) > 500 else '')}\n```")
            embed.set_author(name=f"{ctx.author.display_name} rolled a dice {number} times",
                            icon_url="https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif")
        embed.title = f"The current number is: {rand_num}"
        await ctx.send(embed=embed)

    @commands.command(name='flip', aliases=['coin', 'coinflip'], description="Flip a coin")
    async def flip(self, ctx: FurinaCtx, number: Optional[int] = 1) -> None:
        embed = self.bot.embed
        if number == 1 or number not in range(1, 1000):
            rand_flip: List[str] = np.random.choice(["Head", "Tail"], size=100).tolist()[-1]
            embed.set_author(name=f"{ctx.author.display_name} flipped a coin",
                            icon_url="https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif")
        else:
            seq: List[str] = np.random.choice(["Head", "Tail"], size=100*number).tolist()
            rand_flip = seq[-1]
            seq = [seq_[0] for seq_ in seq]
            embed.add_field(name="History:", value=f"```\n{''.join(seq[:500]) + ('...' if len(seq) > 500 else '')}\n```")
            embed.set_author(name=f"{ctx.author.display_name} flipped a coin {number} times",
                            icon_url="https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif")
        embed.title = f"{rand_flip}"
        await ctx.send(embed=embed)

    @commands.command(name='8ball', description="Ask the magic 8 ball")
    async def magic_eight_ball(self, ctx: FurinaCtx, *, question: str) -> None:
        answers: List[str] = [
            "It is certain",
            "It is decidedly so",
            "Without a doubt",
            "Yes - definitely",
            "You may rely on it",
            "As I see it, yes",
            "Most likely",
            "Outlook good",
            "Yes",
            "Signs point to yes",
            "Don't count on it",
            "My reply is no",
            "My sources say no",
            "Outlook not so good",
            "Very doubtful",
            "Reply hazy, try again",
            "Ask again later",
            "Better not tell you now",
            "Cannot predict now",
            "Concentrate and ask again"]
        embed = self.bot.embed
        embed.set_author(name=f"{ctx.author.display_name} asked the magic 8 ball", 
                         icon_url=r"https://th.bing.com/th/id/R.94318dc029cf3858ebbd4a5bd95617d9?rik=%2bjjVGtbqXgWhQA&pid=ImgRaw&r=0")
        embed.description = f"> {question}\n- **Magic 8 Ball:** `{np.random.choice(answers)}`"
        await ctx.send(embed=embed)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Fun(bot))

