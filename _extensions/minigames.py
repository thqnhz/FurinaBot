from __future__ import annotations
import asyncio, discord, random, string
from discord import app_commands, Embed, ButtonStyle
from discord.ext import commands
from typing import TYPE_CHECKING, List, Dict
from collections import Counter

from .utils import Utils


if TYPE_CHECKING:
    from bot import Furina


class RockPaperScissorButton(discord.ui.Button):
    def __init__(self, number: int):
        super().__init__()
        if number == 0:
            self.label = 'Rock'
            self.emoji = '\u270a'
        elif number == 1:
            self.label = 'Paper'
            self.emoji = '\u270b'
        else:
            self.label = 'Scissor'
            self.emoji = '\u270c'
        self.style = ButtonStyle.secondary

    def converter(self) -> int:
        if self.label == "Rock":
            return -1
        elif self.label == "Paper":
            return 0
        else:
            return 1

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RockPaperScissor = self.view
        if view.move == 0:
            view.player_one = interaction.user
            view.embed.add_field(name="Player 1", value=interaction.user.mention)
            view.move += 1
            await interaction.response.edit_message(embed=view.embed, view=view)
            view.moves.append(self.converter())
        else:
            if interaction.user == view.player_one:
                return await interaction.response.send_message("You can't play with yourself!\n-# || Or can you? Hello Michael, Vsauce here||", ephemeral=True)
            view.player_two = interaction.user
            view.embed.add_field(name="Player 2", value=interaction.user.mention, inline=False)
            await interaction.response.edit_message(embed=view.embed, view=view)
            view.moves.append(self.converter())
            for child in view.children:
                child.disabled = True
            view.stop()
            winner: int | discord.User = view.check_winner()
            if isinstance(winner, int):
                view.embed.description = "### Draw!"
            else:
                view.embed.description = f"### {winner.mention} WON!"
            await interaction.edit_original_response(embed=view.embed, view=view)


class RockPaperScissor(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.move: int = 0
        self.player_one: discord.User | None = None
        self.moves: List[int] = []
        self.player_two: discord.User | None = None
        for i in range(3):
            self.add_item(RockPaperScissorButton(i))
        self.embed: Embed = Embed().set_author(name="Rock Paper Scissor")

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

        self.embed.set_footer(text="Timed out due to inactive. You have no enemies")
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
        

class Wordle(discord.ui.View):
    def __init__(self, *, bot: Furina, word: str):
        super().__init__(timeout=None)
        self.word = word
        self.bot = bot
        self.attempt: int = 6
        self.embed = Embed(title="WORDLE", description="").set_footer(text="Coded by ThanhZ")
        self.alphabet: str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.message: discord.Message

        # a status dict to check if the letter is not yet guessed (0), wrong letter (1), wrong position (2) or correct (3)
        self.STATUS: Dict[str, int] = {
            'UNUSED':      0,
            'NOT_IN_WORD': 1,
            'WRONG_POS':   2,
            'CORRECT':     3
        }

        # a list to store the status of the letters in alphabetical order, init with 26 0s
        self.available: List[int] = [self.STATUS['UNUSED']]*26

        # update the availability right away to get the keyboard field
        self.update_available_characters()

    @property
    def is_over(self) -> bool:
        """Is the game over or not"""
        return self.attempt == 0

    def check_guess(self, guess: str) -> str:
        """
        Check the user's input and update the availabilities afterward
        
        Parameters
        -----------
        guess: `str`
            User's input
        
        Returns
        -----------
        `str`
            A `string` of emojis to represent the result, consists of :green_square: for correct,
            :yellow_square: for wrong pos and :black_large_square: for wrong letter
        """
        result = [""] * len(self.word)
        word_counter = Counter(self.word)

        # correct square
        for i in range(len(self.word)):
            if guess[i] == self.word[i]:
                result[i] = ":green_square:"
                word_counter[guess[i]] -= 1
                letter_index = self.alphabet.index(guess[i])
                self.available[letter_index] = self.STATUS['CORRECT']
                
        # wrong position square or wrong letter square
        for i in range(len(self.word)):
            # if the square is already correct, don't change it
            if result[i] != "":
                continue

            letter_index = self.alphabet.index(guess[i])
            if guess[i] in word_counter and word_counter[guess[i]] > 0:
                result[i] = ":yellow_square:"
                word_counter[guess[i]] -= 1

                # status priority: correct (3) > wrong pos (2) > wrong letter (1) > not yet guessed (0)
                # so if the status of the current pos is already correct, don't change it
                if self.available[letter_index] != self.STATUS['CORRECT']:
                    self.available[letter_index] = self.STATUS['WRONG_POS']
            else:
                result[i] = ":black_large_square:"

                # as above, wrong letter can only replace not yet guessed square
                # so we need to check if the value is lower than wrong pos (2)
                if self.available[letter_index] < self.STATUS['WRONG_POS']:
                        self.available[letter_index] = self.STATUS['NOT_IN_WORD']

        self.update_available_characters()
        return "".join(result)

    def update_available_characters(self):
        """Update letters availability"""
        keyboard_layout = [
            'QWERTYUIOP',
            'ASDFGHJKL',
            'ZXCVBNM'
        ]

        available = ""
        tab = 0
        for row in keyboard_layout:
            available += ' '*tab*2 # half space blank unicode character
            for letter in row:
                letter_index = self.alphabet.index(letter)
                status = self.available[letter_index]

                if status == self.STATUS['CORRECT']:
                    available += f":green_square:`{letter}` "
                elif status == self.STATUS['WRONG_POS']:
                    available += f":yellow_square:`{letter}` "
                elif status == self.STATUS['NOT_IN_WORD']:
                    available += f":black_large_square:`{letter}` "
                else: # status == self.STATUS['UNUSED']
                    available += f":white_large_square:`{letter}` "
            available += "\n"
            tab += 1
        self.embed.clear_fields()
        self.embed.add_field(name="Keyboard", value=available)

    @discord.ui.button(label="Guess", emoji="\U0001f4dd")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WordleModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.guess.lower() not in self.bot.words:
            return await interaction.followup.send(f"`{modal.guess}` is not a real word!", ephemeral=True)

        if self.is_over:
            return await interaction.followup.send("The game is over, your guess didn't count.", ephemeral=True)

        self.attempt -= 1 # update the attempt property as soon as possible so self.is_over is updated
        result = self.check_guess(modal.guess)
        self.embed.description += f"`{modal.guess}` {result} by {interaction.user.mention}\n"
        self.remaining_attempt_button.label = f"Attempts: {self.attempt}"
            
        # nếu kết quả là 5 ký tự xanh hoặc hết lượt đoán
        if result == (":green_square:" * 5) or self.is_over:
            button.disabled = True
            self.embed.description += f"The word is: `{self.word}`"
            self.add_item(LookUpButton(self.word))

            if result == (":green_square:" * 5):
                button.style = ButtonStyle.success
                button.label = "You WON!"
            else:
                button.style = ButtonStyle.danger
                button.label = "You Lost!"
        await interaction.edit_original_response(embed=self.embed, view=self)

        if self.is_over:
            await asyncio.sleep(300)
            self.remove_item(self.children[2])
            self.stop()
            await interaction.edit_original_response(view=self)

    @discord.ui.button(label="Attempts: 6", emoji="\U0001f4ad", disabled=True)
    async def remaining_attempt_button(self, _: discord.Interaction, _b: discord.ui.Button):
        pass


class WordleModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(timeout=None, title="Wordle")
        self.text_input = discord.ui.TextInput(label="Type in your guess", min_length=5, max_length=5)
        self.add_item(self.text_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.guess = self.text_input.value.upper()


class LookUpButton(discord.ui.Button):
    def __init__(self, word: str):
        super().__init__(style=ButtonStyle.secondary, label="Look Up", emoji="\U0001f310")
        self.word = word

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        view = await Utils.dictionary_call(self.word)
        await interaction.followup.send(embed=view.embeds[0], view=view)


class Minigames(commands.Cog):
    """Các Minigame bạn có thể chơi"""
    def __init__(self, bot: "Furina"):
        self.bot = bot
        self.words: List[str] = self.bot.words

    @commands.hybrid_command(name='tictactoe', aliases=['ttt', 'xo'], description="XO minigame")
    async def tic_tac_toe(self, ctx: commands.Context):
        view: TicTacToe = TicTacToe()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(name='rockpaperscissor', aliases=['keobuabao'], description="Kéo Búa Bao minigame")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def keo_bua_bao(self, ctx: commands.Context):
        view: RockPaperScissor = RockPaperScissor()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(name='wordle', description="Wordle minigame")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def wordle(self, ctx: commands.Context):
        word: str = random.choice(self.words)
        while len(word) != 5 or any(char not in string.ascii_letters for char in word):
            word = random.choice(self.words)
        view = Wordle(bot=self.bot, word=word.upper())
        view.message = await ctx.reply(embed=view.embed, view=view)


async def setup(bot: Furina):
    await bot.add_cog(Minigames(bot))

