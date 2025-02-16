from __future__ import annotations

import ast, asyncio, discord
from discord import app_commands, Embed, ButtonStyle
from discord.ext import commands
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from collections import Counter

from .utils import Utils


if TYPE_CHECKING:
    from bot import Furina


class RPSButton(discord.ui.Button):
    LABEL_TO_NUMBER = {
        "Rock": -1,
        "Paper": 0,
        "Scissor": 1
    }
    LABELS = ["Rock",   "Paper",  "Scissor"]
    EMOJIS = ["\u270a", "\u270b", "\u270c"]
    def __init__(self, number: int):
        super().__init__(
            style=ButtonStyle.secondary,
            label=self.LABELS[number],
            emoji=self.EMOJIS[number]
        )

    async def add_player(self, *, view: RPSView, interaction: discord.Interaction) -> int:
        """
        Add the player to the view and update the embed

        Returns
        -----------
        `int`
            - Number of players in the game
        """
        view.players[interaction.user] = self.LABEL_TO_NUMBER[self.label]
        view.embed.add_field(name=f"Player {len(view.players)}", value=interaction.user.mention)
        await interaction.response.edit_message(embed=view.embed, view=view)
        return len(view.players)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: RPSView = self.view

        if interaction.user in view.players:
            return await interaction.response.send_message("You can't play with yourself!\n"
                                                           "-# || Or can you? Hello Michael, Vsauce here||",
                                                           ephemeral=True)

        players_count = await self.add_player(view=view, interaction=interaction)
        if players_count == 2:
            winner = view.check_winner()
            if isinstance(winner, int):
                view.embed.description = "### Draw!"
            else:
                view.embed.description = f"### {winner.mention} WON!"
            await interaction.edit_original_response(embed=view.embed, view=view)
            

class RPSView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        # A dict to store players and their move
        self.players: Dict[discord.User, int] = {}
        for i in range(3):
            self.add_item(RPSButton(i))
        self.embed = Embed().set_author(name="Rock Paper Scissor")

    def check_winner(self) -> discord.User | int:
        """
        Check the winner of the game

        Returns
        -----------
        `discord.User | int`
            - If the result is 0, it's a draw
            - Else it's the discord.User who won
        """
        self.disable_buttons()
        players = list(self.players.keys())
        moves   = list(self.players.values())
        # Draw
        if moves[0] == moves[1]:
            return 0
        # If the result is 1, player 2 wins, else player 1 wins
        result = (moves[1] - moves[0]) % 3
        return players[1] if result == 1 else players[0]

    def disable_buttons(self) -> None:
        """Disable all the buttons in the view"""
        self.stop()
        for button in self.children:
            button.disabled = True

    async def on_timeout(self) -> None:
        self.disable_buttons()
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
        WordleLetterStatus.WRONG_POS: "<:A_YELLOW:1334893955900510238>",
        WordleLetterStatus.CORRECT: "<:A_GREEN:1333452875770363946>"
    },
    "B": {
        WordleLetterStatus.UNUSED: "<:B_WHITE:1312797215781032026>",
        WordleLetterStatus.INCORRECT: "<:B_BLACK:1312800814397657139>",
        WordleLetterStatus.WRONG_POS: "<:B_YELLOW:1334893986380517466>",
        WordleLetterStatus.CORRECT: "<:B_GREEN:1333452899333967925>"
    },
    "C": {
        WordleLetterStatus.UNUSED: "<:C_WHITE:1312798886703927356>",
        WordleLetterStatus.INCORRECT: "<:C_BLACK:1312800832898469920>",
        WordleLetterStatus.WRONG_POS: "<:C_YELLOW:1334894020433940573>",
        WordleLetterStatus.CORRECT: "<:C_GREEN:1333452926395486218>"
    },
    "D": {
        WordleLetterStatus.UNUSED: "<:D_WHITE:1312798918722977913>",
        WordleLetterStatus.INCORRECT: "<:D_BLACK:1312800855610621962>",
        WordleLetterStatus.WRONG_POS: "<:D_YELLOW:1334894047482871890>",
        WordleLetterStatus.CORRECT: "<:D_GREEN:1333452950265401416>"
    },
    "E": {
        WordleLetterStatus.UNUSED: "<:E_WHITE:1312798955439919134>",
        WordleLetterStatus.INCORRECT: "<:E_BLACK:1312800873776414720>",
        WordleLetterStatus.WRONG_POS: "<:E_YELLOW:1334894071344402514>",
        WordleLetterStatus.CORRECT: "<:E_GREEN:1333452970964291627>"
    },
    "F": {
        WordleLetterStatus.UNUSED: "<:F_WHITE:1312798979821666325>",
        WordleLetterStatus.INCORRECT: "<:F_BLACK:1312800893024079992>",
        WordleLetterStatus.WRONG_POS: "<:F_YELLOW:1334894098456379442>",
        WordleLetterStatus.CORRECT: "<:F_GREEN:1333453018116526111>"
    },
    "G": {
        WordleLetterStatus.UNUSED: "<:G_WHITE:1312799003821477970>",
        WordleLetterStatus.INCORRECT: "<:G_BLACK:1312800908677222400>",
        WordleLetterStatus.WRONG_POS: "<:G_YELLOW:1334894123139993711>",
        WordleLetterStatus.CORRECT: "<:G_GREEN:1333453039939354666>"
    },
    "H": {
        WordleLetterStatus.UNUSED: "<:H_WHITE:1312799031583309865>",
        WordleLetterStatus.INCORRECT: "<:H_BLACK:1312800924611248221>",
        WordleLetterStatus.WRONG_POS: "<:H_YELLOW:1334894146867167272>",
        WordleLetterStatus.CORRECT: "<:H_GREEN:1333453063738101842>"
    },
    "I": {
        WordleLetterStatus.UNUSED: "<:I_WHITE:1312799057436999740>",
        WordleLetterStatus.INCORRECT: "<:I_BLACK:1312800943183626333>",
        WordleLetterStatus.WRONG_POS: "<:I_YELLOW:1334894174021091351>",
        WordleLetterStatus.CORRECT: "<:I_GREEN:1333453087024742480>"
    },
    "J": {
        WordleLetterStatus.UNUSED: "<:J_WHITE:1312799083651399731>",
        WordleLetterStatus.INCORRECT: "<:J_BLACK:1312800980621852712>",
        WordleLetterStatus.WRONG_POS: "<:J_YELLOW:1334894198180151408>",
        WordleLetterStatus.CORRECT: "<:J_GREEN:1333453107300012184>"
    },
    "K": {
        WordleLetterStatus.UNUSED: "<:K_WHITE:1312799111958892616>",
        WordleLetterStatus.INCORRECT: "<:K_BLACK:1312800997696995389>",
        WordleLetterStatus.WRONG_POS: "<:K_YELLOW:1334894217129885829>",
        WordleLetterStatus.CORRECT: "<:K_GREEN:1333453128858730548>"
    },
    "L": {
        WordleLetterStatus.UNUSED: "<:L_WHITE:1312799137858846761>",
        WordleLetterStatus.INCORRECT: "<:L_BLACK:1312801016915296326>",
        WordleLetterStatus.WRONG_POS: "<:L_YELLOW:1334894246490144860>",
        WordleLetterStatus.CORRECT: "<:L_GREEN:1333453152736907324>"
    },
    "M": {
        WordleLetterStatus.UNUSED: "<:M_WHITE:1312799162508640306>",
        WordleLetterStatus.INCORRECT: "<:M_BLACK:1312801033100988507>",
        WordleLetterStatus.WRONG_POS: "<:M_YELLOW:1334894270360064083>",
        WordleLetterStatus.CORRECT: "<:M_GREEN:1333453178838057081>"
    },
    "N": {
        WordleLetterStatus.UNUSED: "<:N_WHITE:1312799180506398811>",
        WordleLetterStatus.INCORRECT: "<:N_BLACK:1312801779452350554>",
        WordleLetterStatus.WRONG_POS: "<:N_YELLOW:1334894289548738601>",
        WordleLetterStatus.CORRECT: "<:N_GREEN:1333453201772380260>"
    },
    "O": {
        WordleLetterStatus.UNUSED: "<:O_WHITE:1312799196969042032>",
        WordleLetterStatus.INCORRECT: "<:O_BLACK:1312801794438467634>",
        WordleLetterStatus.WRONG_POS: "<:O_YELLOW:1334894319110455326>",
        WordleLetterStatus.CORRECT: "<:O_GREEN:1333453225969582100>"
    },
    "P": {
        WordleLetterStatus.UNUSED: "<:P_WHITE:1312799212416532580>",
        WordleLetterStatus.INCORRECT: "<:P_BLACK:1312801811891224626>",
        WordleLetterStatus.WRONG_POS: "<:P_YELLOW:1334894345630908597>",
        WordleLetterStatus.CORRECT: "<:P_GREEN:1333453251860889732>"
    },
    "Q": {
        WordleLetterStatus.UNUSED: "<:Q_WHITE:1312799230544314428>",
        WordleLetterStatus.INCORRECT: "<:Q_BLACK:1312801828680761406>",
        WordleLetterStatus.WRONG_POS: "<:Q_YELLOW:1334894367831359742>",
        WordleLetterStatus.CORRECT: "<:Q_GREEN:1333453271448162435>"
    },
    "R": {
        WordleLetterStatus.UNUSED: "<:R_WHITE:1312799249427075142>",
        WordleLetterStatus.INCORRECT: "<:R_BLACK:1312801845491662879>",
        WordleLetterStatus.WRONG_POS: "<:R_YELLOW:1334894389478162493>",
        WordleLetterStatus.CORRECT: "<:R_GREEN:1333453294802047112>"
    },
    "S": {
        WordleLetterStatus.UNUSED: "<:S_WHITE:1312799268096053298>",
        WordleLetterStatus.INCORRECT: "<:S_BLACK:1312801865288777748>",
        WordleLetterStatus.WRONG_POS: "<:S_YELLOW:1334894410403414139>",
        WordleLetterStatus.CORRECT: "<:S_GREEN:1333453317812256828>"
    },
    "T": {
        WordleLetterStatus.UNUSED: "<:T_WHITE:1312799286022639717>",
        WordleLetterStatus.INCORRECT: "<:T_BLACK:1312801885723295834>",
        WordleLetterStatus.WRONG_POS: "<:T_YELLOW:1334894434231259177>",
        WordleLetterStatus.CORRECT: "<:T_GREEN:1333453338209161326>"
    },
    "U": {
        WordleLetterStatus.UNUSED: "<:U_WHITE:1312799302397071432>",
        WordleLetterStatus.INCORRECT: "<:U_BLACK:1312801903226392607>",
        WordleLetterStatus.WRONG_POS: "<:U_YELLOW:1334894456419127326>",
        WordleLetterStatus.CORRECT: "<:U_GREEN:1333453360862330972>"
    },
    "V": {
        WordleLetterStatus.UNUSED: "<:V_WHITE:1312799321208651857>",
        WordleLetterStatus.INCORRECT: "<:V_BLACK:1312801919307219035>",
        WordleLetterStatus.WRONG_POS: "<:V_YELLOW:1334894482386190336>",
        WordleLetterStatus.CORRECT: "<:V_GREEN:1333453386342994033>"
    },
    "W": {
        WordleLetterStatus.UNUSED: "<:W_WHITE:1312799341068419102>",
        WordleLetterStatus.INCORRECT: "<:W_BLACK:1312801939075108975>",
        WordleLetterStatus.WRONG_POS: "<:W_YELLOW:1334894496412078223>",
        WordleLetterStatus.CORRECT: "<:W_GREEN:1333453407163387935>"
    },
    "X": {
        WordleLetterStatus.UNUSED: "<:X_WHITE:1312799359615893664>",
        WordleLetterStatus.INCORRECT: "<:X_BLACK:1312801955760050196>",
        WordleLetterStatus.WRONG_POS: "<:X_YELLOW:1334894517458964543>",
        WordleLetterStatus.CORRECT: "<:X_GREEN:1333453429149925448>"
    },
    "Y": {
        WordleLetterStatus.UNUSED: "<:Y_WHITE:1312799375399063553>",
        WordleLetterStatus.INCORRECT: "<:Y_BLACK:1312801971371114607>",
        WordleLetterStatus.WRONG_POS: "<:Y_YELLOW:1334894537054752838>",
        WordleLetterStatus.CORRECT: "<:Y_GREEN:1333453448796180593>"
    },
    "Z": {
        WordleLetterStatus.UNUSED: "<:Z_WHITE:1312799391840604222>",
        WordleLetterStatus.INCORRECT: "<:Z_BLACK:1312801987074719844>",
        WordleLetterStatus.WRONG_POS: "<:Z_YELLOW:1334894554200936498>",
        WordleLetterStatus.CORRECT: "<:Z_GREEN:1333453471612932210>"
    }
}


class Wordle(discord.ui.View):
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    def __init__(self, *, bot: Furina, word: str):
        super().__init__(timeout=None)
        self.word = word
        self.bot = bot
        self.attempt: int = 6
        self.embed = Embed(title=f"WORDLE ({len(word)} LETTERS)", description="", color=0x2F3136).set_footer(text="Coded by ThanhZ")
        self.message: discord.Message
        self._is_over = False

        # a list to store the status of the letters in alphabetical order, init with 26 0s
        self.available: List[WordleLetterStatus] = [WordleLetterStatus.UNUSED]*26

        # update the availability right away to get the keyboard field
        self.update_available_characters()

    @property
    def is_over(self) -> bool:
        """Is the game over or not"""
        return self.attempt == 0 or self._is_over

    def get_letter_emoji(self, letter: str, status: WordleLetterStatus) -> str:
        """Get the emoji for the letter based on the status"""
        return WORDLE_EMOJIS[letter][status]
    
    def check_guess(self, guess: str) -> str:
        """
        Check the user's input and update the availabilities afterward
        
        Parameters
        -----------
        guess: `str`
            - User's input
        
        Returns
        -----------
        `str`
            - A string of emojis to represent the result, consists of `<:X_Y:ID>`s where X = letter, Y = status and ID = emoji id
        """
        result, word_counter = self.check_green_square(guess)
        # using all() to check if the result is all green squares
        if all("GREEN" in letter for letter in result):
            self._is_over = True
        else: 
            result = self.check_yellow_black_square(guess, result=result, word_counter=word_counter)
        self.update_available_characters()
        return "".join(result)
        
    def check_green_square(self, guess: str) -> Tuple[List[str], Counter]:
        """Check the correct letters in the guess"""
        result = [""] * len(self.word)
        word_counter = Counter(self.word)
        for i, char in enumerate(guess):
            if char == self.word[i]:
                result[i] = self.get_letter_emoji(char, WordleLetterStatus.CORRECT)
                word_counter[char] -= 1
                letter_index = self.ALPHABET.index(char)
                self.available[letter_index] = WordleLetterStatus.CORRECT
        return result, word_counter
    
    def check_yellow_black_square(self, guess: str, *, result: List[str], word_counter: Counter) -> List[str]:
        """Check the wrong position and incorrect letters in the guess"""
        for i, char in enumerate(guess):
            # if the square is already correct, don't change it
            if "GREEN" in result[i]:
                continue

            letter_index = self.ALPHABET.index(char)
            if char in self.word and word_counter[char] > 0:
                result[i] = self.get_letter_emoji(char, WordleLetterStatus.WRONG_POS)
                word_counter[char] -= 1

                # status priority: green (3) > yellow (2) > black (1) > white (0)
                # so if the status of the current pos is already correct, don't change it
                if self.available[letter_index] != WordleLetterStatus.CORRECT:
                    self.available[letter_index] = WordleLetterStatus.WRONG_POS
            else:
                result[i] = self.get_letter_emoji(guess[i], WordleLetterStatus.INCORRECT)

                # as above, black square can only replace white square
                if self.available[letter_index] == WordleLetterStatus.UNUSED:
                        self.available[letter_index] = WordleLetterStatus.INCORRECT
        return result

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
                letter_index = self.ALPHABET.index(letter)
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
        if modal.guess == "":
            return

        if self.is_over:
            return await interaction.followup.send("The game is over, your guess didn't count.", ephemeral=True)
        
        async with self.bot.cs.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{modal.guess.lower()}") as response:
            if response.status != 200:
                return await interaction.followup.send(f"`{modal.guess}` is not a real word!", ephemeral=True)

        self.attempt -= 1 # update the attempt property as soon as possible so self.is_over is updated
        result = self.check_guess(modal.guess)
        self.embed.description += f"{result} by {interaction.user.mention}\n"
        self.remaining_attempt_button.label = f"Attempts: {self.attempt}"
            
        # if win is True or no more attempts left
        if self.is_over:
            button.disabled = True
            self.embed.description += f"### The word is: `{self.word}`"
            self.add_item(LookUpButton(self.word))

            if self.attempt > 0:
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
    def __init__(self, letters: int):
        super().__init__(timeout=180, title=f"Wordle ({letters} LETTERS)")
        self.text_input = discord.ui.TextInput(label="Type in your guess", placeholder="...", min_length=letters, max_length=letters)
        self.add_item(self.text_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.guess = self.text_input.value.upper()

    async def on_timeout(self) -> None:
        self.guess = ""
        self.stop()


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

    @commands.hybrid_command(name='tictactoe', aliases=['ttt', 'xo'], description="XO minigame")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def tic_tac_toe(self, ctx: commands.Context):
        view: TicTacToe = TicTacToe()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(name='rockpaperscissor', aliases=['keobuabao'], description="Rock Paper Scissor minigame")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def keo_bua_bao(self, ctx: commands.Context):
        view = RPSView()
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
        await ctx.defer()
        async with self.bot.cs.get(f"https://random-word-api.vercel.app/api?length={letters}") as response:
            word: str = ast.literal_eval(await response.text())[0]
        view = Wordle(bot=self.bot, word=word.upper())
        view.message = await ctx.reply(embed=view.embed, view=view)


async def setup(bot: Furina):
    await bot.add_cog(Minigames(bot))