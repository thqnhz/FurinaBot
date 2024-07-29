from typing_extensions import Self

import discord
from discord import Embed, ButtonStyle
from discord.ext import commands
from typing import List


class RockPaperScissorButton(discord.ui.Button):
    def __init__(self, number: int):
        super().__init__()
        if number == 0:
            self.label = 'Búa'
            self.emoji = '\u270a'
            self.style = ButtonStyle.secondary
        elif number == 1:
            self.label = 'Bao'
            self.emoji = '\u270b'
            self.style = ButtonStyle.secondary
        else:
            self.label = 'Kéo'
            self.emoji = '\u270c'
            self.style = ButtonStyle.secondary

    def converter(self) -> int:
        if self.label == "Búa":
            return -1
        elif self.label == "Bao":
            return 0
        else:
            return 1

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RockPaperScissor = self.view
        if view.move == 0:
            view.player_one = interaction.user
            view.embed.add_field(name="Người chơi 1", value=interaction.user.mention)
        else:
            if interaction.user == view.player_one:
                return await interaction.response.send_message("Không thể chơi với chính mình", ephemeral=True)
            view.player_two = interaction.user
            view.embed.add_field(name="Người chơi 2", value=interaction.user.mention, inline=False)
        await interaction.response.edit_message(embed=view.embed, view=view)
        view.moves.append(self.converter())
        if view.move == 1:
            for child in view.children:
                child.disabled = True
            view.stop()
            winner: int | discord.User = view.check_winner()
            if isinstance(winner, int):
                view.embed.description = "### Hòa!"
            else:
                view.embed.description = f"### {winner.mention} Thắng!"
            await interaction.edit_original_response(embed=view.embed, view=view)
        view.move += 1


class RockPaperScissor(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.move: int = 0
        self.player_one: discord.User | None = None
        self.moves: list[int] = []
        self.player_two: discord.User | None = None
        for i in range(3):
            self.add_item(RockPaperScissorButton(i))
        self.embed: Embed = Embed().set_author(name="Kéo Búa Bao")

    def check_winner(self) -> discord.User | int:
        # Check Hòa
        if self.moves[0] == self.moves[1]:
            return 0

        result: int = self.moves[1] - self.moves[0]
        if result == 1 or result == -2:
            # Check player two thắng
            return self.player_two
        return self.player_one


class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        super().__init__(style=ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        embed: Embed = Embed()
        if state in (view.X, view.O):
            return

        if view.current_player == view.X:
            self.style = ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            embed.set_author(name="Lượt của O")
        else:
            self.style = ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            embed.set_author(name="Lượt của X")

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                embed.set_author(name="X THẮNG!")
            elif winner == view.O:
                embed.set_author(name="O THẮNG!")
            else:
                embed.set_author(name="HÒA!")

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(embed=embed, view=view)


class TicTacToe(discord.ui.View):
    children: List[TicTacToeButton]
    X: int = -1
    O: int = 1
    Tie: int = 2

    def __init__(self):
        super().__init__()
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check đường thẳng
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check đường chéo
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        # Check hòa
        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None


class Minigames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return True
        # TODO: Thêm check để lệnh chỉ được thực hiện ở kênh bot-commands

    @commands.hybrid_command(name='tictactoe', aliases=['ttt', 'xo'], description="XO minigame")
    async def tic_tac_toe(self, ctx: commands.Context):
        embed: Embed = Embed().set_author(name="X đi trước")
        await ctx.reply(embed=embed, view=TicTacToe())

    @commands.hybrid_command(name='rockpaperscissor', aliases=['keobuabao'], description="Kéo Búa Bao minigame")
    async def keo_bua_bao(self, ctx: commands.Context):
        embed: Embed = Embed().set_author(name="Kéo Búa Bao")
        view: discord.ui.View = RockPaperScissor()
        view.message = await ctx.reply(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Minigames(bot))

