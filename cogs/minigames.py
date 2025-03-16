from __future__ import annotations


import ast
import asyncio
import logging
import os
from abc import abstractmethod
from collections import Counter
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, TYPE_CHECKING


import discord
from discord import app_commands, ui, Color, Embed, ButtonStyle, Message, Interaction, User
from discord.ext import commands


from cogs.utility.sql import MinigamesSQL
from .utils import Utils
from cogs.utility.views import PaginatedView


if TYPE_CHECKING:
    from bot import FurinaBot


class RPSButton(ui.Button):
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

    async def add_player(self, *, view: RPSView, interaction: Interaction) -> int:
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

    async def callback(self, interaction: Interaction):
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
            

class RPSView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        # A dict to store players and their move
        self.players: Dict[User, int] = {}
        for i in range(3):
            self.add_item(RPSButton(i))
        self.embed = Embed().set_author(name="Rock Paper Scissor")

    def check_winner(self) -> User | int:
        """
        Check the winner of the game

        Returns
        -----------
        `User | int`
            - If the result is 0, it's a draw
            - Else it's the User who won
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


class TicTacToeButton(ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int):
        super().__init__(style=ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: Interaction):
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


class TicTacToe(ui.View):
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
        self.player_one: User | None = None
        self.player_two: User | None = None
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


WORDLE_EMOJIS: Dict[str, Dict[WordleLetterStatus, str]]


class WordleABC(ui.View):
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    def __init__(self, *, bot: FurinaBot, word: str, owner: User, solo: bool, attempt: int) -> None:
        super().__init__(timeout=600)
        self.bot = bot
        self.word = word
        self.owner = owner
        self.solo = solo
        self.attempt = attempt
        
        self._is_winning = False
        self._availability: List[WordleLetterStatus] = [WordleLetterStatus.UNUSED] * len(self.ALPHABET)

        self.update_availabilities()
        self.message: Message

    @property
    def is_over(self) -> bool:
        """Whether the game is over or not"""
        return self.attempt == 0 or self._is_winning
    
    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)

    async def update_game_status(self, game_name: str, win: bool):
        async with self.bot.pool.acquire() as db:
            await db.execute("""INSERT INTO singleplayer_games (game_id, game_name, user_id, attempts, win)
                                VALUES ($1, $2, $3, $4, $5)
                                ON CONFLICT (game_id) DO UPDATE SET
                                attempts = EXCLUDED.attempts,
                                win = EXCLUDED.win""",
                            self.message.id, game_name, self.owner.id, self.attempt, win)


    def update_availabilities(self):
        """Update letters availability"""
        keyboard_layout = [
            'QWERTYUIOP',
            'ASDFGHJKL',
            'ZXCVBNM'
        ]

        availabilities = ""
        tab = 0
        for row in keyboard_layout:
            availabilities += ' '*tab*2 # half space blank unicode character
            for letter in row:
                letter_index = self.ALPHABET.index(letter)
                status = self._availability[letter_index]
                availabilities += self.get_letter_emoji(letter, status)
            availabilities += "\n"
            tab += 1
        self.update_keyboard_field(availabilities)

    @abstractmethod
    def update_keyboard_field(self, availabilities: str) -> None:
        pass

    def get_letter_emoji(self, letter: str, status: WordleLetterStatus) -> str:
        """Get the emoji for the letter based on the status"""
        return WORDLE_EMOJIS[letter][status]

    def check_green_square(self, guess: str) -> Tuple[List[str], Counter]:
        """Check the correct letters in the guess"""
        result = [""] * len(self.word)
        word_counter = Counter(self.word)
        for i, char in enumerate(guess):
            if char == self.word[i]:
                result[i] = self.get_letter_emoji(char, WordleLetterStatus.CORRECT)
                word_counter[char] -= 1
                letter_index = self.ALPHABET.index(char)
                self._availability[letter_index] = WordleLetterStatus.CORRECT
        return result, word_counter
    
    def check_yellow_and_black_square(self, guess: str, *, result: List[str], word_counter: Counter) -> List[str]:
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
                if self._availability[letter_index] != WordleLetterStatus.CORRECT:
                    self._availability[letter_index] = WordleLetterStatus.WRONG_POS
            else:
                result[i] = self.get_letter_emoji(guess[i], WordleLetterStatus.INCORRECT)

                # as above, black square can only replace white square
                if self._availability[letter_index] == WordleLetterStatus.UNUSED:
                        self._availability[letter_index] = WordleLetterStatus.INCORRECT
        return result

    @abstractmethod
    async def validate_guess(self, guess: str):
        """Whether the guess is a valid word or not"""
        pass

    @abstractmethod
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
        pass

    @ui.button(emoji="\U0001f4ad", disabled=True)
    async def remaining_attempt_button(self, _: Interaction, _b: ui.Button):
        pass


class Wordle(WordleABC):
    def __init__(self, *, bot: FurinaBot, word: str, owner: User, solo: bool):
        self.embed = bot.embed
        self.embed.title = f"WORDLE ({len(word)} LETTERS)"
        self.embed.description = ""
        self.embed.color = 0x2F3136
        self.embed.set_footer(text="Coded by ThanhZ | v0.3.2-beta")
        super().__init__(bot=bot, word=word, owner=owner, solo=solo, attempt=6)
        self.helped_guess: WordleHelpGuessSelect = WordleHelpGuessSelect()
        self.selected_guess: Optional[str] = None
        self.remaining_attempt_button.label = f"Attempts: {self.attempt}"
    
    def check_guess(self, guess: str) -> str:
        result, word_counter = self.check_green_square(guess)
        # using all() to check if the result is all green squares
        if all("GREEN" in letter for letter in result):
            self._is_winning = True
        else: 
            result = self.check_yellow_and_black_square(guess, result=result, word_counter=word_counter)
        self.update_availabilities()
        return "".join(result)

    def update_keyboard_field(self, availabilities) -> None:
        self.embed.clear_fields()
        self.embed.add_field(name="Keyboard", value=availabilities)

    async def validate_guess(self, guess: str) -> int:
        async with self.bot.cs.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{guess.lower()}") as response:
                return response.status

    async def get_guessandguesser(self, interaction: Interaction) -> Union[Tuple[str, str]]:
        if self.selected_guess:
            await interaction.response.defer()
            selected_guess = self.selected_guess
            guess = selected_guess.split()[0]
            guesser = selected_guess.split()[1]
            self.selected_guess = None
        else:
            modal = WordleModal(letters=len(self.word))
            await interaction.response.send_modal(modal)
            await modal.wait()
            if modal.guess == "":
                return
            guess = modal.guess
            guesser = interaction.user.mention
            status = await self.validate_guess(guess=guess)
            if status != 200:
                return await interaction.followup.send(f"`{guess}` is not a real word!", ephemeral=True)
        return guess, guesser

    async def on_timeout(self) -> None:
        await super().on_timeout()
        self.remove_item(self.children[2])
        await self.update_game_status(game_name="wordle", win=self._is_winning)

    @ui.button(label="Guess", emoji="\U0001f4dd")
    async def guess_button(self, interaction: Interaction, button: ui.Button):
        guess, guesser = await self.get_guessandguesser(interaction)
        
        try:
            for option in self.helped_guess.options:
                if option.label.lower() == guess.lower():
                    self.helped_guess.options.remove(option)
                    break
            if len(self.helped_guess.options) == 0:
                self.remove_item(self.helped_guess)
        except ValueError:
            pass

        # if the guess is not from the command runner
        if interaction.user != self.owner and self.solo:
            if len(self.helped_guess.options) < 25:
                self.add_item(self.helped_guess) if self.helped_guess not in self.children else None
                self.helped_guess.append_option(
                    discord.SelectOption(label=guess.capitalize(), 
                                         value=f"{guess.upper()} {interaction.user.mention}", 
                                         description=f"by {interaction.user.display_name}")
                )
                await interaction.edit_original_response(view=self)
                return await interaction.followup.send(f"Added `{guess}` to help guess list", ephemeral=True)
            else:
                return await interaction.followup.send("There are already enough help guesses. Try again later", ephemeral=True)

        self.attempt -= 1
        result = self.check_guess(guess)
        self.embed.description += f"{result} by {guesser}\n"
        self.remaining_attempt_button.label = f"Attempts: {self.attempt}"
            
        # if is_winning is True or attempt is 0
        if self.is_over:
            button.disabled = True
            self.embed.description += f"### The word is: `{self.word}`"
            self.add_item(LookUpButton(self.word))
            for child in self.children:
                if isinstance(child, WordleHelpGuessSelect):
                    self.remove_item(child)
            if self._is_winning:
                self.embed.color = Color.green()
                button.style = ButtonStyle.success
                button.label = "You WON!"
            else:
                self.embed.color = Color.red()
                button.style = ButtonStyle.danger
                button.label = "You Lost!"
        await interaction.edit_original_response(embed=self.embed, view=self)
        await self.update_game_status(game_name="wordle", win=self._is_winning)


class Letterle(WordleABC):
    def __init__(self, *, bot: FurinaBot, letter: str, owner: User, init_guess: str):
        self.embed = bot.embed
        self.embed.title = "LETTERLE"
        self.embed.description = ""
        self.embed.set_footer(text="Coded by ThanhZ | v0.3.1-beta")
        super().__init__(bot=bot, word=letter, owner=owner, solo=False, attempt=24)
        self.init_guess = init_guess
        self.remaining_attempt_button.label = f"Attempts: {self.attempt}"
        for letter in self.ALPHABET:
            if letter != init_guess:
                self.select_guess.add_option(
                    label=letter, 
                    value=letter, 
                    emoji=self.get_letter_emoji(letter, WordleLetterStatus.UNUSED)
                )

    def check_guess(self, guess: str) -> str:
        result, _ = self.check_green_square(guess)
        if "GREEN" in result[0]:
            self._is_winning = True
        else: 
            result = self.mark_black_square(guess)
        self.update_availabilities()
        return "".join(result)

    def mark_black_square(self, guess: str) -> str:
        letter_index = self.ALPHABET.index(guess)
        self._availability[letter_index] = WordleLetterStatus.INCORRECT
        return self.get_letter_emoji(guess, WordleLetterStatus.INCORRECT)

    
    def update_keyboard_field(self, availabilities) -> None:
        self.embed.clear_fields()
        self.embed.add_field(name="Keyboard", value=availabilities)

    async def on_timeout(self) -> None:
        await super().on_timeout()
        await self.update_game_status(game_name="letterle", win=self._is_winning)

    @ui.select(placeholder="Select a letter")
    async def select_guess(self, interaction: Interaction, select: ui.Select):
        await interaction.response.defer()
        guess = interaction.data["values"][0]
        guesser = interaction.user
        for option in select.options:
            if option.value == guess:
                select.options.remove(option)
        await interaction.edit_original_response(view=self)
        self.attempt -= 1
        self.remaining_attempt_button.label = f"Attempts: {self.attempt}"
        result = self.check_guess(guess)
        self.embed.description += f"{result} by {guesser.mention}\n"
        if "GREEN" in result:
            self._is_winning = True
        if self.is_over:
            select.disabled = True
            self.embed.description += f"### The letter is: `{self.word}`"
            self.embed.color = Color.green() if self._is_winning else Color.red()
        await self.update_game_status(game_name="letterle", win=self._is_winning)
        await interaction.edit_original_response(embed=self.embed, view=self)


class WordleModal(ui.Modal):
    def __init__(self, letters: int):
        super().__init__(timeout=180, title=f"WORDLE ({letters} LETTERS)")
        self.text_input = ui.TextInput(label="Type in your guess", placeholder="...", min_length=letters, max_length=letters)
        self.add_item(self.text_input)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        self.guess = self.text_input.value.upper()

    async def on_timeout(self) -> None:
        self.guess = ""
        self.stop()


class LookUpButton(ui.Button):
    def __init__(self, word: str):
        super().__init__(style=ButtonStyle.secondary, label="Look Up", emoji="\U0001f310", row=0)
        self.word = word

    async def callback(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        view = await Utils.dictionary_call(self.word)
        await interaction.followup.send(embed=view.embeds[0], view=view)


class WordleHelpGuessSelect(ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select a helped guess", options=[], min_values=1, max_values=1, row=1)

    async def callback(self, interaction: Interaction):
        assert self.view is not None
        view: Wordle = self.view
        await interaction.response.defer()
        if interaction.user == view.owner:
            view.selected_guess = self.values[0]


class Minigames(commands.GroupCog, group_name="minigame"):
    """Some minigames that you can play"""
    def __init__(self, bot: FurinaBot):
        self.bot = bot

    async def cog_load(self) -> None:
        await self.update_wordle_emojis()

    async def update_wordle_emojis(self) -> None:
        global WORDLE_EMOJIS
        WORDLE_EMOJIS = {letter: {} for letter in Wordle.ALPHABET}

        emojis = await self.bot.fetch_application_emojis()
        for emoji in emojis:
            if "_BLACK" in emoji.name:
                WORDLE_EMOJIS[emoji.name[0]][WordleLetterStatus.INCORRECT] = str(emoji)
            elif "_GREEN" in emoji.name:
                WORDLE_EMOJIS[emoji.name[0]][WordleLetterStatus.CORRECT] = str(emoji)
            elif "_WHITE" in emoji.name:
                WORDLE_EMOJIS[emoji.name[0]][WordleLetterStatus.UNUSED] = str(emoji)
            elif "_YELLOW" in emoji.name:
                WORDLE_EMOJIS[emoji.name[0]][WordleLetterStatus.WRONG_POS] = str(emoji)
        for letter in WORDLE_EMOJIS:
            if len(WORDLE_EMOJIS[letter]) != 4:
                logging.warning(f"Missing emojis for wordle game")
                return await self.upload_missing_emojis()

    async def upload_missing_emojis(self) -> None:
        logging.info("Uploading missing wordle emojis...")

        from pathlib import Path
        from tqdm import tqdm
        wordle_letters_path = Path("./assets/wordle")
        filenames = os.listdir(wordle_letters_path)
        for _, filename in enumerate(tqdm(filenames, desc="Uploading", unit=" emojis"), 1):
            with open(Path(f"{wordle_letters_path}/{filename}"), "rb") as file:
                try:
                    await self.bot.create_application_emoji(name=filename.split(".")[0], image=file.read())
                except discord.HTTPException:
                    # This is when the emoji failed to upload because the emoji name already exists.
                    # We don't need to care about this.
                    pass
            await asyncio.sleep(0.5)
        logging.info("Uploaded missing wordle emojis")
        return await self.update_wordle_emojis()

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

    @app_commands.command(name='wordle', description="Wordle minigame")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def wordle(self,
                     interaction: Interaction,
                     letters: app_commands.Range[int, 3, 8] = 5,
                     solo: bool = True):
        """Wordle minigame

        A game where you have 6 guesses and a word to guess. If your guess has a letter that is in the word, it becomes yellow, if your guess has a letter that in the correct position with the word, it becomes green, otherwise it becomes black. The game ends when you are out of guesses or you guessed the correct word.

        Parameters
        -----------
        letters: `app_commands.Range[int, 3, 8] = 5`
            - Number of letters for this game (3-8), default to 5
        solo: `bool = True`
            - Solo mode only allows others to help, if you want others to guess straight in, make it False
        """
        await interaction.response.defer()
        async with self.bot.cs.get(f"https://random-word-api.vercel.app/api?length={letters}") as response:
            word: str = ast.literal_eval(await response.text())[0]
        view = Wordle(bot=self.bot, word=word.upper(), owner=interaction.user, solo=solo)
        await interaction.followup.send(embed=view.embed, view=view)
        view.message = await interaction.original_response()
        await view.update_game_status(game_name="wordle", win=False)

    @app_commands.command(name='letterle', description="Letterle minigame")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def letterle(self, interaction: Interaction, first_guess: str = ""):
        """Letterle minigame

        A game where you have 25 guesses and a letter to guess. If you guess the correct letter within 25 guesses you win.

        Parameters
        -----------
        first_guess: `str = ""`
            - The first letter to guess, leave it blank for random one
        """
        await interaction.response.defer()
        first_guess = first_guess.upper()
        from random import randint
        letter = Letterle.ALPHABET[randint(0, 25)]
        if first_guess not in Letterle.ALPHABET or len(first_guess) != 1:
            first_guess = Letterle.ALPHABET[randint(0, 25)]
        view = Letterle(bot=self.bot, letter=letter, owner=interaction.user, init_guess=first_guess)
        embed = view.embed
        init_result = view.check_guess(first_guess)
        embed.description = f"{init_result} by {interaction.user.mention}\n"
        if "GREEN" in init_result:
            embed.description += "First Guess Correct!!!"
            embed.color = Color.green()
            await interaction.followup.send(embed=embed)
            win = True
        else:
            await interaction.followup.send(embed=embed, view=view)
            win = False
        view.message = await interaction.original_response()
        await view.update_game_status(game_name="letterle", win=win)

    stats = app_commands.Group(name='stats', description="View minigame stats")

    @stats.command(name='all', description="View all minigames stats")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_all(self, interaction: Interaction):
        await interaction.response.defer()
        embeds: List[Embed] = []
        rows = await MinigamesSQL(self.bot.pool).get_minigame_stats_all()
        sorted_by_minigame: Dict[str, List[Dict[str, int]]] = {}
        for row in rows:
            minigame = row['game_name']
            user_stats = {
                'user_id': row['user_id'],
                'wins': row['wins']
            }
            if minigame not in sorted_by_minigame:
                sorted_by_minigame[minigame] = []
            sorted_by_minigame[minigame].append(user_stats)
        for minigame, user_stats_list in sorted_by_minigame.items():
            embed = self.bot.embed
            embed.title = minigame.capitalize()
            embed.description = ""
            for index, user_stats in enumerate(user_stats_list, 1):
                embed.description += f"{index}. <@{user_stats['user_id']}>: {user_stats['wins']} wins\n"
            embeds.append(embed)
        view = PaginatedView(timeout=180, embeds=embeds)
        await interaction.followup.send(embed=view.embeds[0], view=view)
        view.message = await interaction.original_response()
            
    @stats.command(name='user', description="View a specific user's minigame stats")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_user(self, interaction: Interaction, user: User = None):
        """
        View a specific user's minigame stats

        Parameters
        -----------
        user: `User = None`
            - Leave it blank to see your own.
        """
        await interaction.response.defer()
        user = user or interaction.user
        rows = await MinigamesSQL(self.bot.pool).get_minigame_stats_user(user.id)
        embed = self.bot.embed
        embed.title = f"Minigame Stats"
        embed.description = f"User: {user.mention}"
        for row in rows:
            embed.add_field(name=row['game_name'].capitalize(), 
                            value=f"Total games played: `{row['total_games']:04d}`\nWins: `{row['wins']:04d}`\nLosses: `{row['losses']:04d}`", 
                            inline=False)
        await interaction.followup.send(embed=embed)

    @stats.command(name='wordle', description="View wordle minigame stats")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_wordle(self, interaction: Interaction):
        """View wordle minigame stats"""
        await self.get_minigame_stats(interaction, "wordle")

    @stats.command(name='letterle', description="View letterle minigame stats")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_letterle(self, interaction: Interaction):
        """View letterle minigame stats"""
        await self.get_minigame_stats(interaction, "letterle")

    async def get_minigame_stats(self, interaction: Interaction, minigame: str):
        await interaction.response.defer()
        rows_top = await MinigamesSQL(self.bot.pool).get_top_players_by_minigame(minigame)
        embed = self.bot.embed
        embed.title = f"{minigame.capitalize()} Minigame Stats"
        top_players = ""
        for index, row in enumerate(rows_top, 1):
            top_players += f"{index}. <@{row['user_id']}>: `{row['wins']:04d}` wins\n"
        if not top_players:
            top_players = "There is no one here"
        embed.add_field(name=f"Top 3 {minigame} players\n", value=top_players)
        rows_bottom = await MinigamesSQL(self.bot.pool).get_bottom_players_by_minigame(minigame)
        bottom_players = ""
        for index, row in enumerate(rows_bottom, 1):
            bottom_players += f"{index}. <@{row['user_id']}>: `{row['losses']:04d}` loses\n"
        if not bottom_players:
            bottom_players = "No one is here either"
        embed.add_field(name=f"Bottom 3 {minigame} players\n", value=bottom_players, inline=False)
        await interaction.followup.send(embed=embed)



async def setup(bot: FurinaBot):
    await bot.add_cog(Minigames(bot))