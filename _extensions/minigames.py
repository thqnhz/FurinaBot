from __future__ import annotations

import asyncio, discord, random, string
from discord import app_commands, Embed, ButtonStyle
from discord.ext import commands
from enum import Enum
from typing import TYPE_CHECKING, List, Tuple, Optional
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
        

class WordleLetterStatus(Enum):
    UNUSED    = 0,
    INCORRECT = 1,
    WRONG_POS = 2,
    CORRECT   = 3

# TODO: When discord.py 2.5 finally on pypi, update automatically upload and save the emojis so i don't need it anymore
WORDLE_EMOJIS = {
    "A": {
        WordleLetterStatus.UNUSED: "<:A_WHITE:1312797015683371078>",
        WordleLetterStatus.INCORRECT: "<:A_BLACK:1312800796206960762>",
        WordleLetterStatus.WRONG_POS: "<:A_YELLOW:1333452077698912318>",
        WordleLetterStatus.CORRECT: "<:A_GREEN:1333452875770363946>"
    },
    "B": {
        WordleLetterStatus.UNUSED: "<:B_WHITE:1312797215781032026>",
        WordleLetterStatus.INCORRECT: "<:B_BLACK:1312800814397657139>",
        WordleLetterStatus.WRONG_POS: "<:B_YELLOW:1333452116152418355>",
        WordleLetterStatus.CORRECT: "<:B_GREEN:1333452899333967925>"
    },
    "C": {
        WordleLetterStatus.UNUSED: "<:C_WHITE:1312798886703927356>",
        WordleLetterStatus.INCORRECT: "<:C_BLACK:1312800832898469920>",
        WordleLetterStatus.WRONG_POS: "<:C_YELLOW:1333452149987868805>",
        WordleLetterStatus.CORRECT: "<:C_GREEN:1333452926395486218>"
    },
    "D": {
        WordleLetterStatus.UNUSED: "<:D_WHITE:1312798918722977913>",
        WordleLetterStatus.INCORRECT: "<:D_BLACK:1312800855610621962>",
        WordleLetterStatus.WRONG_POS: "<:D_YELLOW:1333452224637964378>",
        WordleLetterStatus.CORRECT: "<:D_GREEN:1333452950265401416>"
    },
    "E": {
        WordleLetterStatus.UNUSED: "<:E_WHITE:1312798955439919134>",
        WordleLetterStatus.INCORRECT: "<:E_BLACK:1312800873776414720>",
        WordleLetterStatus.WRONG_POS: "<:E_YELLOW:1333452273610788925>",
        WordleLetterStatus.CORRECT: "<:E_GREEN:1333452970964291627>"
    },
    "F": {
        WordleLetterStatus.UNUSED: "<:F_WHITE:1312798979821666325>",
        WordleLetterStatus.INCORRECT: "<:F_BLACK:1312800893024079992>",
        WordleLetterStatus.WRONG_POS: "<:F_YELLOW:1333452303361118218>",
        WordleLetterStatus.CORRECT: "<:F_GREEN:1333453018116526111>"
    },
    "G": {
        WordleLetterStatus.UNUSED: "<:G_WHITE:1312799003821477970>",
        WordleLetterStatus.INCORRECT: "<:G_BLACK:1312800908677222400>",
        WordleLetterStatus.WRONG_POS: "<:G_YELLOW:1333452334063292527>",
        WordleLetterStatus.CORRECT: "<:G_GREEN:1333453039939354666>"
    },
    "H": {
        WordleLetterStatus.UNUSED: "<:H_WHITE:1312799031583309865>",
        WordleLetterStatus.INCORRECT: "<:H_BLACK:1312800924611248221>",
        WordleLetterStatus.WRONG_POS: "<:H_YELLOW:1333452369928654980>",
        WordleLetterStatus.CORRECT: "<:H_GREEN:1333453063738101842>"
    },
    "I": {
        WordleLetterStatus.UNUSED: "<:I_WHITE:1312799057436999740>",
        WordleLetterStatus.INCORRECT: "<:I_BLACK:1312800943183626333>",
        WordleLetterStatus.WRONG_POS: "<:I_YELLOW:1333452399670591558>",
        WordleLetterStatus.CORRECT: "<:I_GREEN:1333453087024742480>"
    },
    "J": {
        WordleLetterStatus.UNUSED: "<:J_WHITE:1312799083651399731>",
        WordleLetterStatus.INCORRECT: "<:J_BLACK:1312800980621852712>",
        WordleLetterStatus.WRONG_POS: "<:J_YELLOW:1333452480645697546>",
        WordleLetterStatus.CORRECT: "<:J_GREEN:1333453107300012184>"
    },
    "K": {
        WordleLetterStatus.UNUSED: "<:K_WHITE:1312799111958892616>",
        WordleLetterStatus.INCORRECT: "<:K_BLACK:1312800997696995389>",
        WordleLetterStatus.WRONG_POS: "<:K_YELLOW:1333452507556483145>",
        WordleLetterStatus.CORRECT: "<:K_GREEN:1333453128858730548>"
    },
    "L": {
        WordleLetterStatus.UNUSED: "<:L_WHITE:1312799137858846761>",
        WordleLetterStatus.INCORRECT: "<:L_BLACK:1312801016915296326>",
        WordleLetterStatus.WRONG_POS: "<:L_YELLOW:1333452531245781012>",
        WordleLetterStatus.CORRECT: "<:L_GREEN:1333453152736907324>"
    },
    "M": {
        WordleLetterStatus.UNUSED: "<:M_WHITE:1312799162508640306>",
        WordleLetterStatus.INCORRECT: "<:M_BLACK:1312801033100988507>",
        WordleLetterStatus.WRONG_POS: "<:M_YELLOW:1333452560073490515>",
        WordleLetterStatus.CORRECT: "<:M_GREEN:1333453178838057081>"
    },
    "N": {
        WordleLetterStatus.UNUSED: "<:N_WHITE:1312799180506398811>",
        WordleLetterStatus.INCORRECT: "<:N_BLACK:1312801779452350554>",
        WordleLetterStatus.WRONG_POS: "<:N_YELLOW:1333452583314128968>",
        WordleLetterStatus.CORRECT: "<:N_GREEN:1333453201772380260>"
    },
    "O": {
        WordleLetterStatus.UNUSED: "<:O_WHITE:1312799196969042032>",
        WordleLetterStatus.INCORRECT: "<:O_BLACK:1312801794438467634>",
        WordleLetterStatus.WRONG_POS: "<:O_YELLOW:1333452606164697149>",
        WordleLetterStatus.CORRECT: "<:O_GREEN:1333453225969582100>"
    },
    "P": {
        WordleLetterStatus.UNUSED: "<:P_WHITE:1312799212416532580>",
        WordleLetterStatus.INCORRECT: "<:P_BLACK:1312801811891224626>",
        WordleLetterStatus.WRONG_POS: "<:P_YELLOW:1333452628893499423>",
        WordleLetterStatus.CORRECT: "<:P_GREEN:1333453251860889732>"
    },
    "Q": {
        WordleLetterStatus.UNUSED: "<:Q_WHITE:1312799230544314428>",
        WordleLetterStatus.INCORRECT: "<:Q_BLACK:1312801828680761406>",
        WordleLetterStatus.WRONG_POS: "<:Q_YELLOW:1333452651165126697>",
        WordleLetterStatus.CORRECT: "<:Q_GREEN:1333453271448162435>"
    },
    "R": {
        WordleLetterStatus.UNUSED: "<:R_WHITE:1312799249427075142>",
        WordleLetterStatus.INCORRECT: "<:R_BLACK:1312801845491662879>",
        WordleLetterStatus.WRONG_POS: "<:R_YELLOW:1333452671268552808>",
        WordleLetterStatus.CORRECT: "<:R_GREEN:1333453294802047112>"
    },
    "S": {
        WordleLetterStatus.UNUSED: "<:S_WHITE:1312799268096053298>",
        WordleLetterStatus.INCORRECT: "<:S_BLACK:1312801865288777748>",
        WordleLetterStatus.WRONG_POS: "<:S_YELLOW:1333452692483215360>",
        WordleLetterStatus.CORRECT: "<:S_GREEN:1333453317812256828>"
    },
    "T": {
        WordleLetterStatus.UNUSED: "<:T_WHITE:1312799286022639717>",
        WordleLetterStatus.INCORRECT: "<:T_BLACK:1312801885723295834>",
        WordleLetterStatus.WRONG_POS: "<:T_YELLOW:1333452711932330049>",
        WordleLetterStatus.CORRECT: "<:T_GREEN:1333453338209161326>"
    },
    "U": {
        WordleLetterStatus.UNUSED: "<:U_WHITE:1312799302397071432>",
        WordleLetterStatus.INCORRECT: "<:U_BLACK:1312801903226392607>",
        WordleLetterStatus.WRONG_POS: "<:U_YELLOW:1333452732849197206>",
        WordleLetterStatus.CORRECT: "<:U_GREEN:1333453360862330972>"
    },
    "V": {
        WordleLetterStatus.UNUSED: "<:V_WHITE:1312799321208651857>",
        WordleLetterStatus.INCORRECT: "<:V_BLACK:1312801919307219035>",
        WordleLetterStatus.WRONG_POS: "<:V_YELLOW:1333452754043011114>",
        WordleLetterStatus.CORRECT: "<:V_GREEN:1333453386342994033>"
    },
    "W": {
        WordleLetterStatus.UNUSED: "<:W_WHITE:1312799341068419102>",
        WordleLetterStatus.INCORRECT: "<:W_BLACK:1312801939075108975>",
        WordleLetterStatus.WRONG_POS: "<:W_YELLOW:1333452777191636992>",
        WordleLetterStatus.CORRECT: "<:W_GREEN:1333453407163387935>"
    },
    "X": {
        WordleLetterStatus.UNUSED: "<:X_WHITE:1312799359615893664>",
        WordleLetterStatus.INCORRECT: "<:X_BLACK:1312801955760050196>",
        WordleLetterStatus.WRONG_POS: "<:X_YELLOW:1333452806312431647>",
        WordleLetterStatus.CORRECT: "<:X_GREEN:1333453429149925448>"
    },
    "Y": {
        WordleLetterStatus.UNUSED: "<:Y_WHITE:1312799375399063553>",
        WordleLetterStatus.INCORRECT: "<:Y_BLACK:1312801971371114607>",
        WordleLetterStatus.WRONG_POS: "<:Y_YELLOW:1333452827028230205>",
        WordleLetterStatus.CORRECT: "<:Y_GREEN:1333453448796180593>"
    },
    "Z": {
        WordleLetterStatus.UNUSED: "<:Z_WHITE:1312799391840604222>",
        WordleLetterStatus.INCORRECT: "<:Z_BLACK:1312801987074719844>",
        WordleLetterStatus.WRONG_POS: "<:Z_YELLOW:1333452851745394709>",
        WordleLetterStatus.CORRECT: "<:Z_GREEN:1333453471612932210>"
    }
}


class Wordle(discord.ui.View):
    def __init__(self, *, bot: Furina, word: str):
        super().__init__(timeout=None)
        self.word = word
        self.bot = bot
        self.attempt: int = 6
        self.embed = Embed(title=f"WORDLE ({len(word)} LETTERS)", description="").set_footer(text="Coded by ThanhZ")
        self.alphabet: str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        self.message: discord.Message

        # a list to store the status of the letters in alphabetical order, init with 26 0s
        self.available: List[WordleLetterStatus] = [WordleLetterStatus.UNUSED]*26

        # update the availability right away to get the keyboard field
        self.update_available_characters()

    @property
    def is_over(self) -> bool:
        """Is the game over or not"""
        return self.attempt == 0

    def get_letter_emoji(self, letter: str, status: WordleLetterStatus) -> str:
        return WORDLE_EMOJIS[letter][status]
    
    def check_guess(self, guess: str) -> Tuple[str, bool]:
        """
        Check the user's input and update the availabilities afterward
        
        Parameters
        -----------
        guess: `str`
            User's input
        
        Returns
        -----------
        `tuple[str, bool]`
            A `string` of emojis to represent the result, consists of :green_square: for correct,
            :yellow_square: for wrong pos and :black_large_square: for incorrect and a bool indicates
            if the guess is correct
        """
        result = [""] * len(self.word)
        word_counter = Counter(self.word)

        # correct square
        correct_count: int = 0
        for i in range(len(self.word)):
            if guess[i] == self.word[i]:
                correct_count += 1
                result[i] = self.get_letter_emoji(guess[i], WordleLetterStatus.CORRECT)
                word_counter[guess[i]] -= 1
                letter_index = self.alphabet.index(guess[i])
                self.available[letter_index] = WordleLetterStatus.CORRECT

        if correct_count == len(self.word):
            self.update_available_characters()
            return "".join(result), True
                
        # wrong position square or wrong letter square
        for i in range(len(self.word)):
            # if the square is already correct, don't change it
            if result[i] != "":
                continue

            letter_index = self.alphabet.index(guess[i])
            if guess[i] in word_counter and word_counter[guess[i]] > 0:
                result[i] = self.get_letter_emoji(guess[i], WordleLetterStatus.WRONG_POS)
                word_counter[guess[i]] -= 1

                # status priority: correct (3) > wrong pos (2) > wrong letter (1) > not yet guessed (0)
                # so if the status of the current pos is already correct, don't change it
                if self.available[letter_index] != WordleLetterStatus.CORRECT:
                    self.available[letter_index] = WordleLetterStatus.WRONG_POS
            else:
                result[i] = self.get_letter_emoji(guess[i], WordleLetterStatus.INCORRECT)

                # as above, wrong letter can only replace not yet guessed square
                # so we need to check if the value is lower than wrong pos (2)
                if self.available[letter_index].value < WordleLetterStatus.WRONG_POS.value:
                        self.available[letter_index] = WordleLetterStatus.INCORRECT

        self.update_available_characters()
        return "".join(result), False

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
                available += self.get_letter_emoji(letter, status)
            available += "\n"
            tab += 1
        self.embed.clear_fields()
        self.embed.add_field(name="Keyboard", value=available)

    @discord.ui.button(label="Guess", emoji="\U0001f4dd")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WordleModal(letters=len(self.word))
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.guess.lower() not in self.bot.words:
            return await interaction.followup.send(f"`{modal.guess}` is not a real word!", ephemeral=True)

        if self.is_over:
            return await interaction.followup.send("The game is over, your guess didn't count.", ephemeral=True)

        self.attempt -= 1 # update the attempt property as soon as possible so self.is_over is updated
        result, win = self.check_guess(modal.guess)
        self.embed.description += f"{result} by {interaction.user.mention}\n"
        self.remaining_attempt_button.label = f"Attempts: {self.attempt}"
            
        # if win is True or no more attempts left
        if win or self.is_over:
            button.disabled = True
            self.embed.description += f"### The word is: `{self.word}`"
            self.add_item(LookUpButton(self.word))

            if win:
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
    def __init__(self, letters: int = 5):
        super().__init__(timeout=None, title=f"Wordle ({letters} LETTERS)")
        self.text_input = discord.ui.TextInput(label="Type in your guess", min_length=letters, max_length=letters)
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


class Minigames(commands.GroupCog, group_name="minigame"):
    """Các Minigame bạn có thể chơi"""
    def __init__(self, bot: Furina):
        self.bot = bot
        self.words: List[str] = self.bot.words

    @commands.hybrid_command(name='tictactoe', aliases=['ttt', 'xo'], description="XO minigame")
    @app_commands.allowed_installs(guilds=True, users=True)
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
    async def wordle(self, ctx: commands.Context, letters: Optional[app_commands.Range[int, 3, 8]] = 5):
        """
        Wordle minigame

        Parameters
        -----------
        ctx: `commands.Context`
            Context
        letters: `app_commands.Range[int, 3, 8] = 5`
            Number of letters for this game (3-8), default to 5
        """
        word: str = random.choice(self.words)
        while len(word) != letters or any(char not in string.ascii_letters for char in word):
            word = random.choice(self.words)
        view = Wordle(bot=self.bot, word=word.upper())
        view.message = await ctx.reply(embed=view.embed, view=view)


async def setup(bot: Furina):
    await bot.add_cog(Minigames(bot))

