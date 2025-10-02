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

import csv
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from discord import Interaction, Message, app_commands, ui
from discord.ext import commands

from core import FurinaCog, FurinaCtx, settings
from core.views import Container, LayoutView

if TYPE_CHECKING:
    from core import FurinaBot


class Fun(FurinaCog):
    """Funni Commands haha XD"""

    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)
        self.ctx_menu_liemeter = app_commands.ContextMenu(
            name="Lie Detector", callback=self.lie_detector
        )
        self.bot.tree.add_command(self.ctx_menu_liemeter)

        self._fortune_yapping: list[list[str]] | None = None

    @property
    def fortune_yapping(self) -> list[list[str]]:
        if self._fortune_yapping:
            return self._fortune_yapping
        with Path.open(
            Path() / "assets" / "yapping" / "fortune.csv", newline=""
        ) as f:
            reader = csv.reader(f)
            self._fortune_yapping = [
                [str(line) for line in row] for row in reader
            ]
        return self._fortune_yapping

    @property
    def rng(self) -> np.random.Generator:
        """Return a random number generator"""
        return np.random.default_rng()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(
            self.ctx_menu_liemeter.name, type=self.ctx_menu_liemeter.type
        )
        await super().cog_unload()

    async def lie_detector(
        self, interaction: Interaction, message: Message
    ) -> None:
        if message.author.id == self.bot.user.id:
            await interaction.response.send_message("I always tell the truth")
            return
        if self.rng.random() < 0.5:
            await interaction.response.send_message(
                "This message is verified to be the truth"
            )
        else:
            await interaction.response.send_message(
                "https://tenor.com/kXIbVjdMB8x.gif"
            )

    @commands.command(name="fortune", aliases=["lucky", "slip", "fortuneslip"])
    async def fortune_slip_command(
        self, ctx: FurinaCtx, number: int = 1
    ) -> None:
        """Draw a fortune slip

        Give you random fortune from 6 levels, from high to low:
        - Great Fortune
        - Good Fortune
        - Modest Fortune
        - Rising Fortune
        - Misfortune
        - Great Misfortune
        Number of times thinking can only be from `1` to `9999`.
        Otherwise will default to `1`.

        Parameters
        ----------
        number : int, optional
            How many times you want to think before drawing a slip,
            default is `1`
        """
        fortunes: list[str] = [
            "Great Fortune",
            "Good Fortune",
            "Modest Fortune",
            "Rising Fortune",
            "Misfortune",
            "Great Misfortune",
        ]
        fortune_index = self.hashing(
            ctx.author.id, key=settings.FORTUNE_KEY, max_val=5
        )
        yap = self.fortune_yapping[fortune_index][
            self.hashing(
                ctx.author.id, key=settings.FORTUNE_YAPPING_KEY, max_val=4
            )
        ]

        if number == 1 or number not in range(1, 10_000):
            times = "very hard"
        else:
            times = f"{number} times"
        header = f"""
            {ctx.author.mention} thought {times} before drawing a fortune slip
        """
        fortune_section = ui.Section(
            ui.TextDisplay(
                f"### {header}\n## {fortunes[fortune_index]}\n>>> {yap}\n"
            ),
            accessory=ui.Thumbnail(
                "https://upload-static.hoyoverse.com/hoyolab-wiki/2023/08/01/94376896/13b4067ebbc97e7a3577b9358c9c6eb9_8561788766756121179.png?x-oss-process=image%2Fformat%2Cwebp"
            ),
        )
        await ctx.send(
            view=LayoutView(
                Container(
                    fortune_section,
                    ui.TextDisplay(
                        "-# This is just for fun, take it as a grain of salt"
                        " | Coded by ThanhZ"
                    ),
                )
            ),
            silent=True,
        )

    @staticmethod
    def hashing(id_: int, *, key: int, max_val: int) -> int:
        """Hashes the id and the key to an index, day dependent"""
        day_factor = int(time.time()) // 86400
        return (((id_ * 2654435761) ^ key) ^ day_factor) % max_val

    @commands.command(name="dice", aliases=["roll"])
    async def dice_command(self, ctx: FurinaCtx, number: int = 1) -> None:
        """Roll a dice 6

        Roll a dice 6 `number` of times.
        Number of times rolling can only be from `1` to `999`.
        Otherwise will default to `1`.

        Parameters
        ----------
        number : int, optional
            How many times you want to roll the dice, default is `1`
        """
        if number == 1 or number not in range(1, 1000):
            rand_num = self.rng.randint(1, 7)
            header = f"{ctx.author.mention} rolled a dice"
            seq = None
        else:
            seq: list[int] = self.rng.randint(1, 7, size=number).tolist()
            seq: list[str] = [str(seq_) for seq_ in seq]
            rand_num = seq[-1]
            seq: str = " ".join(seq[:100]) + ("..." if len(seq) > 100 else "")
            header = f"{ctx.author.mention} rolled a dice {number} times"
        section = ui.Section(
            ui.TextDisplay("### " + header),
            ui.TextDisplay(f"## {rand_num}"),
            accessory=ui.Thumbnail(
                r"https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif"
            ),
        )
        if seq:
            section.add_item(ui.TextDisplay(f"**History:**\n`{seq}`"))
        view = ui.LayoutView().add_item(
            ui.Container(section).add_item(ui.TextDisplay("-# Coded by ThanhZ"))
        )
        await ctx.send(view=view, silent=True)

    @commands.command(name="flip", aliases=["coin", "coinflip"])
    async def flip_command(self, ctx: FurinaCtx, number: int = 1) -> None:
        """Flip a coin

        Flip a coin `number` of times.
        Number of times flipping can only be from `1` to `999`.
        Otherwise will default to `1`.

        Parameters
        ----------
        number : int, optional
            How many times you want to flip the coin, default is `1`
        """
        if number == 1 or number not in range(1, 1000):
            rand_flip: list[str] = self.rng.choice(["Head", "Tail"])
            header = f"{ctx.author.mention} flipped a coin"
            seq = None
        else:
            seq: list[str] = self.rng.choice(
                ["Head", "Tail"], size=number
            ).tolist()
            rand_flip = seq[-1]
            seq: list[str] = [seq_[0] for seq_ in seq]
            seq: str = " ".join(seq[:100]) + ("..." if len(seq) > 100 else "")
            header = f"{ctx.author.mention} flipped a coin {number} times"
        section = ui.Section(
            ui.TextDisplay("### " + header),
            ui.TextDisplay(f"## {rand_flip}"),
            accessory=ui.Thumbnail(
                r"https://cdn.7tv.app/emote/6175d52effc7244d797d15bf/4x.gif"
            ),
        )
        if seq:
            section.add_item(ui.TextDisplay(f"**History:**\n`{seq}`"))
        view = ui.LayoutView().add_item(
            ui.Container(section).add_item(ui.TextDisplay("-# Coded by ThanhZ"))
        )
        await ctx.send(view=view, silent=True)

    @commands.command(name="8ball")
    async def magic_eight_ball(self, ctx: FurinaCtx, *, question: str) -> None:
        """Ask the magic 8 ball

        The magic 8 ball will answer your question.
        Take the answer as a grain of salt as it is randomized answer.

        Parameters
        ----------
        question : str
            Your question
        """
        answers: list[str] = [
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
            "Concentrate and ask again",
        ]
        section = ui.Section(
            ui.TextDisplay(f"### {ctx.author.mention} asked the magic 8 ball"),
            ui.TextDisplay(f"## {self.rng.choice(answers)}"),
            accessory=ui.Thumbnail(
                r"https://th.bing.com/th/id/R.94318dc029cf3858ebbd4a5bd95617d9?rik=%2bjjVGtbqXgWhQA&pid=ImgRaw&r=0"
            ),
        )
        container = ui.Container(
            section,
            ui.Separator(),
            ui.TextDisplay(f"**Question:**\n>>> {question}"),
            ui.TextDisplay(
                "-# This is just for fun, take it as a grain of salt"
                " | Coded by ThanhZ"
            ),
        )
        await ctx.send(view=ui.LayoutView().add_item(container), silent=True)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Fun(bot))
