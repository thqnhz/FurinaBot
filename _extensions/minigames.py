import discord, nltk, random
from discord import Embed, ButtonStyle
from discord.ext import commands
from typing import List
from nltk.corpus import wordnet
from collections import Counter


class RockPaperScissorButton(discord.ui.Button):
    def __init__(self, number: int):
        super().__init__()
        if number == 0:
            self.label = 'Búa'
            self.emoji = '\u270a'
        elif number == 1:
            self.label = 'Bao'
            self.emoji = '\u270b'
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
            view.move += 1
            await interaction.response.edit_message(embed=view.embed, view=view)
            view.moves.append(self.converter())
        else:
            if interaction.user == view.player_one:
                return await interaction.response.send_message("Không thể chơi với chính mình", ephemeral=True)
            view.player_two = interaction.user
            view.embed.add_field(name="Người chơi 2", value=interaction.user.mention, inline=False)
            await interaction.response.edit_message(embed=view.embed, view=view)
            view.moves.append(self.converter())
            for child in view.children:
                child.disabled = True
            view.stop()
            winner: int | discord.User = view.check_winner()
            if isinstance(winner, int):
                view.embed.description = "### Hòa!"
            else:
                view.embed.description = f"### {winner.mention} Thắng!"
            await interaction.edit_original_response(embed=view.embed, view=view)


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

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        self.embed.set_footer(text="Đã Timeout")
        await self.message.edit(embed=self.embed, view=self)


class TicTacToeButton(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        super().__init__(style=ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if view.current_player == view.X:
            if interaction.user == view.player_two:
                return await interaction.response.send_message("Chưa đến lượt của bạn",
                                                               ephemeral=True)
            if view.player_one is None:
                view.player_one = interaction.user
                view.embed.add_field(name="Người chơi 1", value=view.player_one.mention)
            else:
                if interaction.user != view.player_one:
                    return await interaction.response.send_message("Bạn không nằm trong trò chơi này",
                                                                   ephemeral=True)
            self.style = ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            view.embed.set_author(name="Lượt của O")
        else:
            if interaction.user == view.player_one:
                return await interaction.response.send_message("Chưa đến lượt của bạn",
                                                               ephemeral=True)
            if view.player_two is None:
                view.player_two = interaction.user
                view.embed.add_field(name="Người chơi 2", value=view.player_two.mention)
            else:
                if interaction.user != view.player_two:
                    return await interaction.response.send_message("Bạn không nằm trong trò chơi này",
                                                                   ephemeral=True)
            self.style = ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            view.embed.set_author(name="Lượt của X")

        winner = view.check_board_winner()
        if winner is not None:
            view.embed.set_author(name="")
            if winner == view.X:
                view.embed.description = f"### {view.player_one.mention} Thắng!"
            elif winner == view.O:
                view.embed.description = f"### {view.player_two.mention} Thắng!"
            else:
                view.embed.description = f"### Hòa!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(embed=view.embed, view=view)


class TicTacToe(discord.ui.View):
    children: List[TicTacToeButton]
    X: int = -1
    O: int = 1
    Tie: int = 2

    def __init__(self):
        super().__init__(timeout=300)
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        self.player_one: discord.User | None = None
        self.player_two: discord.User | None = None
        self.embed: Embed = Embed().set_author(name="Tic Tac Toe")

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_board_winner(self):
        # Check đường thẳng (ngang)
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check đường thẳng (dọc)
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

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        self.embed.set_footer(text="Đã Timeout")
        await self.message.edit(embed=self.embed, view=self)
        


# TODO: FINISH THE WORDLE MINIGAME
class Wordle(discord.ui.View):
    def __init__(self, word: str):
        super().__init__(timeout=None)
        self.word: str = word
        self.message: discord.Message | None = None
        self.attempt: int = 6
        self.embed = Embed(title="WORDLE", description="")
        self.embed.set_footer(text="Coded by ThanhZ")

    def check_guess(self, guess: str):
        result = [""] * len(self.word)
        word_counter = Counter(self.word)

        for i in range(len(self.word)):
            if guess[i] == self.word[i]:
                result[i] = ":green_square:"
                word_counter[guess[i]] -= 1

        for i in range(len(self.word)):
            if result[i] == "":
                if guess[i] in word_counter and word_counter[guess[i]] > 0:
                    result[i] = ":yellow_square:"
                    word_counter[guess[i]] -= 1
                else:
                    result[i] = ":black_large_square:"
        return "".join(result)

    @discord.ui.button(label="Đoán", emoji="\U0001f4ad", custom_id="guess_button")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WordleModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        result = self.check_guess(modal.guess.upper())
        self.embed.description += f"`{modal.guess.upper()}` {result}\n"
        self.attempt -= 1
        self.remaining_attempt_button.label = f"Còn lại: {self.attempt}"
        if result == (":green_square:" * 5):
            button.disabled = True
            button.style = ButtonStyle.success
            button.label = "Bạn đã đoán đúng"
            self.embed.description += f"Đáp án là: `{self.word}`"
        if self.attempt == 0:
            button.disabled = True
            button.style = ButtonStyle.danger
            button.label = "Bạn đã thua"
            self.embed.description += f"Đáp án là: `{self.word}`"
        await self.message.edit(embed=self.embed, view=self)

    @discord.ui.button(label="Còn lại: 6", custom_id="remaining_attempt", disabled=True)
    async def remaining_attempt_button(self, _: discord.Interaction, _b: discord.ui.Button):
        pass


class WordleModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(timeout=None, title="Wordle")
        self.text_input = discord.ui.TextInput(label="Nhập dự đoán", min_length=5, max_length=5)
        self.add_item(self.text_input)
        self.guess: str = ""

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.guess = self.text_input.value

class Minigames(commands.Cog):
    """Các Minigame bạn có thể chơi"""
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.words = None

    async def cog_load(self):
        nltk.download("wordnet")
        self.words = list(wordnet.words())


    @commands.hybrid_command(name='tictactoe', aliases=['ttt', 'xo'], description="XO minigame")
    async def tic_tac_toe(self, ctx: commands.Context):
        view: TicTacToe = TicTacToe()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(name='rockpaperscissor', aliases=['keobuabao'], description="Kéo Búa Bao minigame")
    async def keo_bua_bao(self, ctx: commands.Context):
        view: RockPaperScissor = RockPaperScissor()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(name='wordle', description="Wordle minigame")
    async def wordle(self, ctx: commands.Context):
        word = random.choice(self.words)
        while len(word) != 5:
            word = random.choice(self.words)
        view = Wordle(word)
        view.message = await ctx.reply(embed=view.embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Minigames(bot))

