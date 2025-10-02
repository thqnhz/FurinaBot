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

import ast
import asyncio
import logging
import pathlib
import string
from collections import Counter
from enum import IntEnum
from typing import TYPE_CHECKING, ClassVar

import asqlite
import discord
import numpy as np
from discord import (
    ButtonStyle,
    Color,
    Embed,
    Interaction,
    Member,
    Message,
    User,
    app_commands,
    ui,
)
from discord.ext import commands
from tqdm import tqdm

from core import utils
from core.views import Container, LayoutView, PaginatedLayoutView, PaginatedView

if TYPE_CHECKING:
    from core import FurinaBot, FurinaCtx


class RPSButton(ui.Button):
    LABEL_TO_NUMBER: ClassVar[dict[str, int]] = {
        "Rock": -1,
        "Paper": 0,
        "Scissor": 1,
    }
    LABELS: ClassVar[list[str]] = ["Rock", "Paper", "Scissor"]
    EMOJIS: ClassVar[list[str]] = ["\u270a", "\u270b", "\u270c"]

    def __init__(self, number: int) -> None:
        super().__init__(
            style=ButtonStyle.secondary,
            label=self.LABELS[number],
            emoji=self.EMOJIS[number],
        )

    async def add_player(
        self, *, view: RPSView, interaction: Interaction
    ) -> int:
        """
        Add the player to the view and update the embed

        Returns
        -----------
        `int`
            - Number of players in the game
        """
        view.players[interaction.user] = self.LABEL_TO_NUMBER[self.label]
        view.embed.add_field(
            name=f"Player {len(view.players)}", value=interaction.user.mention
        )
        await interaction.response.edit_message(embed=view.embed, view=view)
        return len(view.players)

    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        view: RPSView = self.view

        if interaction.user in view.players:
            await interaction.response.send_message(
                "You can't play with yourself!\n"
                "-# || Or can you? Hello Michael, Vsauce here||",
                ephemeral=True,
            )
            return

        players_count = await self.add_player(
            view=view, interaction=interaction
        )
        if players_count == 2:
            winner = view.check_winner()
            if isinstance(winner, int):
                view.embed.description = "### Draw!"
            else:
                view.embed.description = f"### {winner.mention} WON!"
            await interaction.edit_original_response(
                embed=view.embed, view=view
            )


class RPSView(ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=300)
        # A dict to store players and their move
        self.players: dict[User | Member, int] = {}
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
        moves = list(self.players.values())
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
        self.embed.set_footer(
            text="Timed out due to inactive. You have no enemies"
        )
        await self.message.edit(embed=self.embed, view=self)


class TicTacToeButton(ui.Button["TicTacToe"]):
    def __init__(self, x: int, y: int) -> None:
        super().__init__(style=ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if interaction.user not in view.players:
            await interaction.response.send_message(
                "You are not in this game", ephemeral=True
            )
            return

        if view.current_player == view.X:
            if interaction.user == view.player_two:
                await interaction.response.send_message(
                    "Not your turn yet", ephemeral=True
                )
                return
            if view.player_one is None:
                view.player_one = interaction.user
                view.embed.add_field(
                    name="Player 1", value=view.player_one.mention
                )
            self.style = ButtonStyle.danger
            self.label = "X"
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            view.embed.set_author(name="O's turn")
        else:
            if interaction.user == view.player_one:
                await interaction.response.send_message(
                    "Not your turn yet", ephemeral=True
                )
                return
            if view.player_two is None:
                view.player_two = interaction.user
                view.embed.add_field(
                    name="Player 2", value=view.player_two.mention
                )
            self.style = ButtonStyle.success
            self.label = "O"
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            view.embed.set_author(name="X's turn")

        winner = view.check_board_winner()
        if winner is not None:
            view.embed.set_author(name="")
            if winner == view.X:
                view.embed.description = f"### {view.player_one.mention} Won!"
            elif winner == view.O:
                view.embed.description = f"### {view.player_two.mention} Won!"
            else:
                view.embed.description = "### Draw!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(embed=view.embed, view=view)


class TicTacToe(ui.View):
    children: list[TicTacToeButton]
    X: int = -1
    O: int = 1  # noqa: E741
    Tie: int = 2

    def __init__(self) -> None:
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

    @property
    def players(self) -> tuple[User, User]:
        return self.player_one, self.player_two

    def check_board_winner(self) -> int | None:
        # Check đường thẳng (ngang)
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            if value == -3:
                return self.X

        # Check đường thẳng (dọc)
        for line in range(3):
            value = (
                self.board[0][line] + self.board[1][line] + self.board[2][line]
            )
            if value == 3:
                return self.O
            if value == -3:
                return self.X

        # Check đường chéo
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        if diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        if diag == -3:
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


class WordleLetterStatus(IntEnum):
    UNUSED = 0
    INCORRECT = 1
    WRONG_POS = 2
    CORRECT = 3


class WordleABC(LayoutView):
    """Abstract Base Class for Wordle Minigames"""

    ALPHABET: ClassVar[str] = string.ascii_uppercase
    LETTER_INDEX: ClassVar[dict[str, int]] = {
        letter: i for i, letter in enumerate(ALPHABET)
    }

    def __init__(
        self,
        *,
        bot: FurinaBot,
        word: str,
        owner: User,
        solo: bool,
        attempt: int,
        pool: asqlite.Pool,
    ) -> None:
        self.bot = bot
        self.word = word
        self.owner = owner
        self.solo = solo
        self.attempt = attempt
        self.pool = pool

        self.history: list[str] = []

        self._is_winning = False
        self._availability = [WordleLetterStatus.UNUSED] * len(self.ALPHABET)
        self.message: Message
        super().__init__(self.container, timeout=600)

    @property
    def container(self) -> Container:
        return Container(
            self.header,
            ui.Separator(),
            self.keyboard_section,
            ui.Separator(),
            ui.TextDisplay("-# Coded by ThanhZ | v0.4.0-beta"),
        )

    @property
    def header(self) -> ui.Section:
        game = (
            "## LETTERLE"
            if len(self.word) == 1
            else f"## WORDLE ({len(self.word)} LETTERS)"
        )
        status = (
            ("(WIN)" if self._is_winning else "(LOST)") if self.is_over else ""
        )
        return ui.Section(
            ui.TextDisplay(
                f"{game}\n"
                f"### Player: {self.owner.mention}\n"
                f"**Attempts left:** `{self.attempt}` {status}"
            ),
            accessory=ui.Thumbnail(self.owner.avatar.url),
        )

    @property
    def is_over(self) -> bool:
        """Whether the game is over or not"""
        return self.attempt == 0 or self._is_winning

    @property
    def availabilities(self) -> str:
        KEYBOARD_LAYOUT = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]

        availabilities = ""
        for tab, row in enumerate(KEYBOARD_LAYOUT):
            availabilities += (
                " " * tab * 2
            )  # half space blank unicode character
            for letter in row:
                letter_index = self.ALPHABET.index(letter)
                status = self._availability[letter_index]
                availabilities += self.get_letter_emoji(letter, status)
            availabilities += "\n"
        return availabilities

    @property
    def keyboard_section(self) -> ui.Section:
        return ui.Section(
            self.availabilities,
            accessory=WordleGuessButton(disabled=self.is_over),
        )

    def get_letter_emoji(self, letter: str, status: WordleLetterStatus) -> str:
        """Get the emoji for the letter based on the status"""
        return Minigames.WORDLE_EMOJIS[letter][status]

    async def validate_guess(self, guess: str) -> bool:
        """|coro| |abstractmethod|

        Validating the guess

        Parameters
        ----------
        guess : str
            The guessed word

        Returns
        -------
        bool
            True if the guess is a valid, else False
        """
        raise NotImplementedError

    def check_guess(
        self, guess: str
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        """Compares the guess and the word

        Parameters
        ----------
        guess : str
            The guessed word

        Returns
        -------
        Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]
            A tuple containing three tuples:

            1. Green letters (correct position)
            2. Yellow letters (correct letter, wrong position)
            3. Black letters (letter not in word)
            Empty strings ('') represent no letter
            in that position for that color
        """
        green_letters: list[str] = [""] * len(self.word)
        yellow_letters: list[str] = [""] * len(self.word)
        black_letters: list[str] = [""] * len(self.word)
        counter = Counter(self.word)

        # Check green letters
        for i, char in enumerate(guess):
            if char == self.word[i]:
                green_letters[i] = char
                counter[char] -= 1

        # The guessed word is correct
        if all(green_letters):
            self._is_winning = True
            return (
                tuple(green_letters),
                tuple(yellow_letters),
                tuple(black_letters),
            )

        # Otherwise continue to check yellow and black letters
        for i, char in enumerate(guess):
            if green_letters[i]:
                continue
            if char in self.word and counter[char] > 0:
                yellow_letters[i] = char
                counter[char] -= 1
            else:
                black_letters[i] = char
        return tuple(green_letters), tuple(yellow_letters), tuple(black_letters)

    def update_game_status(self, guess: str) -> None:
        """|abstractmethod|

        Update the container with current game status

        Parameters
        ----------
        guess : str
            The guessed word
        """

    async def process_guess(self, guess: str) -> None:
        """|coro|

        Process the guess and update the message

        Parameters
        ----------
        guess : str
            The guessed word
        """
        self.update_game_status(guess)
        await self.message.edit(view=self)


class WordleView(WordleABC):
    """Wordle Layout View"""

    def __init__(
        self,
        *,
        bot: FurinaBot,
        word: str,
        owner: User,
        solo: bool,
        pool: asqlite.Pool,
        word_db: asqlite.Pool,
    ) -> None:
        self.word_db = word_db

        self.guesses: dict[str, str] = {}
        self.helped_guess: WordleHelpGuessSelect = WordleHelpGuessSelect()

        super().__init__(
            bot=bot, word=word, owner=owner, solo=solo, attempt=6, pool=pool
        )

        self._lookup_button: LookUpButton = LookUpButton(word=self.word)

    @property
    def modal(self) -> WordleModal:
        correct_letters: list[str] = []
        wrong_pos_letters: list[str] = []
        incorrect_letters: list[str] = []
        unused_letters: list[str] = []
        for index, status in enumerate(self._availability):
            if status == WordleLetterStatus.INCORRECT:
                incorrect_letters.append(self.ALPHABET[index])
            elif status == WordleLetterStatus.UNUSED:
                unused_letters.append(self.ALPHABET[index])
            elif status == WordleLetterStatus.WRONG_POS:
                wrong_pos_letters.append(self.ALPHABET[index])
            else:
                correct_letters.append(self.ALPHABET[index])
        return WordleModal(
            letters=len(self.word),
            unused_letters=unused_letters,
            incorrect_letters=incorrect_letters,
            wrong_pos_letters=wrong_pos_letters,
            correct_letters=correct_letters,
        )

    @property
    def guess_display(self) -> ui.TextDisplay:
        if self.history:
            result = [self.guesses[h] for h in self.history]
            return ui.TextDisplay("\n".join(result))
        return ui.TextDisplay("*No guesses yet*")

    @property
    def over_section(self) -> ui.Section:
        return ui.Section(
            ui.TextDisplay(f"### The word is: `{self.word}`"),
            accessory=self._lookup_button,
        )

    @property
    def container(self) -> Container:
        container = Container(
            self.header,
            self.guess_display,
        )
        if self.is_over:
            container.add_item(self.over_section)
            container.accent_color = (
                Color.green() if self._is_winning else Color.red()
            )
        container.add_item(ui.Separator()).add_item(
            ui.TextDisplay("### Keyboard")
        ).add_item(self.keyboard_section)
        if self.helped_guess.options:
            container.add_item(ui.Separator()).add_item(
                ui.ActionRow(self.helped_guess)
            )
        return container

    def update_game_status(self, guess: str) -> None:
        """Update the container with current game status

        Parameters
        ----------
        guess : str
            The guessed word
        """
        green_letters, yellow_letters, black_letters = self.check_guess(guess)
        result = [""] * len(self.word)
        for i in range(len(self.word)):
            letter = None
            status = None
            if green_letters[i]:
                letter = green_letters[i]
                status = WordleLetterStatus.CORRECT
            elif yellow_letters[i]:
                letter = yellow_letters[i]
                status = WordleLetterStatus.WRONG_POS
            elif black_letters[i]:
                letter = black_letters[i]
                status = WordleLetterStatus.INCORRECT

            if letter:
                idx = self.LETTER_INDEX[letter]
                # Because we need to save the best status
                # of the letter, so we get max of the status
                # and the previous status
                self._availability[idx] = max(status, self._availability[idx])
                result[i] = self.get_letter_emoji(letter, status)

        self.guesses[guess] = "".join(result)
        self.history.append(guess)
        self.clear_items()
        self.add_item(self.container)

    async def validate_guess(self, guess: str) -> bool:
        """Validating the guess

        Checking priority: history -> database
        English word database: https://github.com/dwyl/english-words/blob/master/words_alpha.txt

        Parameters
        ----------
        guess : :class:`str`
            The guessed word

        Returns
        -------
        :class:`bool`
            `True` if the guess is a valid word, else `False`
        """
        if guess in self.history:
            return True
        async with self.word_db.acquire() as conn:
            result = await conn.fetchone(
                "SELECT COUNT(*) FROM valid_word WHERE word = ? LIMIT 1", guess
            )
            if result[0] == 1:
                return True
        return False


class WordleGuessButton(ui.Button):
    def __init__(self, *, disabled: bool) -> None:
        super().__init__(label="Guess", emoji="\U0001f4dd", disabled=disabled)

    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        view: WordleView = self.view
        modal = view.modal
        await interaction.response.send_modal(modal)
        await modal.wait()
        if not modal.guess:
            return
        guess = modal.guess
        valid = await view.validate_guess(guess=guess)
        if not valid:
            await interaction.followup.send(
                f"`{guess}` is not in the database!", ephemeral=True
            )
            return

        if view.solo and interaction.user != view.owner:
            if guess not in view.helped_guess.guesses:
                view.helped_guess.guesses.append(guess)
                view.helped_guess.update_options()
                view.clear_items()
                view.add_item(view.container)
                await interaction.edit_original_response(view=view)
                await interaction.followup.send(
                    f"Added `{guess}` to helped list", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"`{guess}` already in the helped list", ephemeral=True
                )
            return

        view.attempt -= 1
        await view.process_guess(guess)


class Letterle(WordleABC):
    def __init__(
        self, *, bot: FurinaBot, letter: str, owner: User, pool: asqlite.Pool
    ) -> None:
        self.buttons: list[LetterleButton] = [
            LetterleButton(self.ALPHABET[i]) for i in range(len(self.ALPHABET))
        ]
        super().__init__(
            bot=bot, word=letter, owner=owner, solo=True, attempt=25, pool=pool
        )

    @property
    def container(self) -> Container:
        container = Container(
            self.header,
            ui.Separator(),
            *[
                ui.ActionRow(*self.buttons[i : i + 4])
                for i in range(0, len(self.ALPHABET), 4)
            ],
        ).add_item(ui.TextDisplay("-# Coded by ThanhZ | v0.4.0-beta"))
        if self.is_over:
            container.accent_color = (
                Color.green() if self._is_winning else Color.red()
            )
        return container


class LetterleButton(ui.Button[Letterle]):
    def __init__(
        self,
        letter: str,
        status: WordleLetterStatus = WordleLetterStatus.UNUSED,
    ) -> None:
        emoji = Minigames.WORDLE_EMOJIS[letter][status]
        super().__init__(emoji=emoji)
        self.letter = letter

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user != self.view.owner:
            await interaction.response.send_message(
                "You can not play this game", ephemeral=True
            )
            return
        assert self.view is not None
        view: Letterle = self.view
        view.attempt -= 1
        button = view.buttons[view.LETTER_INDEX[self.letter]]
        button.disabled = True
        if self.letter == view.word:
            button.emoji = Minigames.WORDLE_EMOJIS[self.letter][
                WordleLetterStatus.CORRECT
            ]
            for child in view.walk_children():
                child.disabled = True
            view._is_winning = True
        else:
            button.emoji = Minigames.WORDLE_EMOJIS[self.letter][
                WordleLetterStatus.INCORRECT
            ]
        view.clear_items()
        view.add_item(view.container)
        await interaction.response.edit_message(view=view)


class WordleModal(ui.Modal):
    def __init__(
        self,
        *,
        letters: int,
        unused_letters: list[str],
        incorrect_letters: list[str],
        wrong_pos_letters: list[str],
        correct_letters: list[str],
    ) -> None:
        super().__init__(timeout=180, title=f"WORDLE ({letters} LETTERS)")
        self.input = ui.TextInput(
            label="Type in your guess",
            placeholder="...",
            min_length=letters,
            max_length=letters,
        )
        self.letter_statuses = ui.Label(
            text="Letter Statuses",
            description=(
                "Open the dropdown menu to see the current game letter statuses"
            ),
            component=ui.Select(
                options=[
                    discord.SelectOption(
                        label="Correct Letters",
                        value="correct",
                        description=" ".join(correct_letters),
                    ),
                    discord.SelectOption(
                        label="Wrong Position Letters",
                        value="wrong_pos",
                        description=" ".join(wrong_pos_letters),
                    ),
                    discord.SelectOption(
                        label="Incorrect Letters",
                        value="incorrect",
                        description=" ".join(incorrect_letters),
                    ),
                    discord.SelectOption(
                        label="Unused Letters",
                        value="unused",
                        description=" ".join(unused_letters),
                    ),
                ],
                required=False
            ),
        )
        self.add_item(self.input)
        self.add_item(self.letter_statuses)
        self.guess: str = ""

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        self.guess = self.input.value.upper()


class LookUpButton(ui.Button):
    def __init__(self, word: str) -> None:
        super().__init__(
            style=ButtonStyle.secondary, label="Look Up", emoji="\U0001f310"
        )
        self.word = word
        self.dict: PaginatedLayoutView | None = None

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        if not self.dict:
            self.dict = await utils.call_dictionary(
                self.word, interaction.client.cs
            )
        await interaction.followup.send(view=self.dict)


class WordleHelpGuessSelect(ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Select a helped guess",
            options=[],
            min_values=1,
            max_values=1,
        )
        self.guesses: list[str] = []

    def update_options(self) -> None:
        self.options.clear()
        for guess in self.guesses[:25]:
            self.add_option(label=guess, value=guess)

    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        view: WordleView = self.view
        if interaction.user != view.owner:
            await interaction.response.send_message(
                "You can not choose helped guess", ephemeral=True
            )
            return
        await interaction.response.defer()
        self.guesses.remove(self.values[0])
        self.update_options()
        self.view.attempt -= 1
        await view.process_guess(self.values[0])


class Minigames(commands.GroupCog, group_name="minigame"):
    """Some minigames that you can play"""

    WORDLE_EMOJIS: ClassVar[dict[str, dict[WordleLetterStatus, str]]]

    def __init__(self, bot: FurinaBot) -> None:
        self.bot = bot
        self.emoji_loading_attempts: int = 0

        self._randomized_words: list[set[str]] = [set() for _ in range(5)]

    async def cog_load(self) -> None:
        self.pool = self.bot.pool
        self.wordle_db = await asqlite.create_pool(
            pathlib.Path() / "db" / "wordle.db"
        )
        await self.__update_wordle_emojis()
        await self.__create_valid_guess_table()
        logging.info("Cog %s has been loaded", self.__cog_name__)

    async def get_random_word(self, length: int) -> str:
        index: int = length - 3
        word_set: set[str] = self._randomized_words[index]
        if word_set:
            return self._randomized_words[index].pop()
        async with self.bot.cs.get(
            f"https://random-word-api.vercel.app/api?words=50&length={length}&type=uppercase"
        ) as response:
            words = set(ast.literal_eval(await response.text()))
        self._randomized_words[index] = words
        return self._randomized_words[index].pop()

    async def __create_valid_guess_table(self) -> None:
        async with self.wordle_db.acquire() as conn, conn.transaction():
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS valid_word
                (
                    word TEXT NOT NULL PRIMARY KEY
                )
                """
            )
            test = await conn.fetchone("SELECT COUNT(*) FROM valid_word")
            if test[0] != 0:
                return
            path = pathlib.Path() / "assets" / "valid_guess"
            files = path.iterdir()
            for f in files:
                words = f.open("r").read().split()
                await conn.executemany(
                    "INSERT INTO valid_word (word) VALUES (?)",
                    [(word,) for word in words],
                )

    async def __update_wordle_emojis(self) -> None:
        if self.emoji_loading_attempts >= 3:
            logging.warning("Failed to load emojis for wordle game")
            return
        Minigames.WORDLE_EMOJIS = {letter: {} for letter in WordleView.ALPHABET}

        emojis = self.bot.app_emojis
        for emoji in emojis:
            name = emoji.name
            id_ = emoji.id
            if "_BLACK" in name:
                Minigames.WORDLE_EMOJIS[name[0]][
                    WordleLetterStatus.INCORRECT
                ] = f"<:{name}:{id_}>"
            elif "_GREEN" in name:
                Minigames.WORDLE_EMOJIS[name[0]][WordleLetterStatus.CORRECT] = (
                    f"<:{name}:{id_}>"
                )
            elif "_WHITE" in name:
                Minigames.WORDLE_EMOJIS[name[0]][WordleLetterStatus.UNUSED] = (
                    f"<:{name}:{id_}>"
                )
            elif "_YELLOW" in name:
                Minigames.WORDLE_EMOJIS[name[0]][
                    WordleLetterStatus.WRONG_POS
                ] = f"<:{name}:{id_}>"

        for letter in self.WORDLE_EMOJIS:
            if len(self.WORDLE_EMOJIS[letter]) != 4:
                logging.warning("Missing emojis for wordle game")
                await self.__upload_missing_emojis()

    async def __upload_missing_emojis(self) -> None:
        logging.info("Uploading missing wordle emojis...")

        wordle_letters_path = pathlib.Path() / "assets" / "wordle"
        filenames = wordle_letters_path.iterdir()
        for _, filename in enumerate(
            tqdm(filenames, desc="Uploading", unit=" emojis"), 1
        ):
            file = (wordle_letters_path / filename).read_bytes()
            try:
                await self.bot.create_application_emoji(
                    name=filename.stem, image=file
                )
            except discord.HTTPException:
                # This is when the emoji failed to upload
                # because the emoji name already exists.
                # We don't need to care about this.
                pass
            await asyncio.sleep(0.5)
        logging.info("Uploaded missing wordle emojis")
        self.emoji_loading_attempts += 1
        await self.__update_wordle_emojis()
        return

    @commands.hybrid_command(
        name="tictactoe", aliases=["ttt", "xo"], description="XO minigame"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    async def tic_tac_toe(self, ctx: FurinaCtx) -> None:
        view = TicTacToe()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(
        name="rockpaperscissor",
        aliases=["keobuabao"],
        description="Rock Paper Scissor minigame",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    async def rps_command(self, ctx: FurinaCtx) -> None:
        view = RPSView()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(name="wordle")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def wordle(
        self,
        ctx: FurinaCtx,
        letters: app_commands.Range[int, 3, 8] = 5,
        *,
        solo: bool = True,
    ) -> None:
        """Wordle minigame

        A game where you have 6 guesses and a word to guess.
        Color square meanings:
        - Green: correct letter in correct position
        - Yellow: correct letter in wrong position
        - Black: incorrect letter
        The game ends when you are out of guesses
        or you guessed the correct word.

        Parameters
        ----------
        letters : Range[int, 3, 8] = 5, optional
            Number of letters in the word
        solo : bool = True, optional
            Whether others can join the game or not
        """
        await ctx.defer()
        word = await self.get_random_word(letters)
        view = WordleView(
            bot=self.bot,
            word=word,
            owner=ctx.author,
            solo=solo,
            pool=self.pool,
            word_db=self.wordle_db,
        )
        view.message = await ctx.send(view=view)

    @commands.hybrid_command(name="letterle")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def letterle(self, ctx: FurinaCtx) -> None:
        """Letterle minigame

        A game where you have 25 guesses and a letter to guess.
        If you guess the correct letter within 25 guesses you win.
        """
        await ctx.defer()
        rng = np.random.default_rng()
        letter = Letterle.ALPHABET[rng.integers(0, 26)]
        view = Letterle(
            bot=self.bot, letter=letter, owner=ctx.author, pool=self.pool
        )
        view.message = await ctx.send(view=view)

    stats = app_commands.Group(name="stats", description="Minigames stats")

    @stats.command(name="all", description="View all minigames stats")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_all(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        embeds: list[Embed] = []
        rows = await self.pool.fetchall(
            """
            WITH ranked_players AS (
                SELECT
                    game_name,
                    user_id,
                    COUNT(*) FILTER (WHERE win = TRUE) AS wins,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_name
                        ORDER BY COUNT(*)
                        FILTER (WHERE win = TRUE) DESC
                    ) AS rank
                FROM
                    singleplayer_games
                GROUP BY
                    game_name, user_id
            )
            SELECT
                game_name,
                user_id,
                wins
            FROM
                ranked_players
            WHERE
                rank <= 3
            ORDER BY
                game_name, rank;
            """
        )
        sorted_by_minigame: dict[str, list[dict[str, int]]] = {}
        for row in rows:
            minigame = row["game_name"]
            user_stats = {"user_id": row["user_id"], "wins": row["wins"]}
            if minigame not in sorted_by_minigame:
                sorted_by_minigame[minigame] = []
            sorted_by_minigame[minigame].append(user_stats)
        for minigame, user_stats_list in sorted_by_minigame.items():
            embed = self.bot.embed
            embed.title = minigame.capitalize()
            embed.description = ""
            for i, user_stats in enumerate(user_stats_list, 1):
                embed.description += (
                    f"{i}. <@{user_stats['user_id']}>:"
                    f" {user_stats['wins']} wins\n"
                )
            embeds.append(embed)
        if not embeds:
            embeds = [self.bot.embed]
            embeds[0].title = "No Game Records"
        view = PaginatedView(timeout=180, embeds=embeds)
        await interaction.followup.send(embed=view.embeds[0], view=view)
        view.message = await interaction.original_response()

    @stats.command(name="user")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_user(
        self, interaction: Interaction, user: User = None
    ) -> None:
        """View a specific user's minigame stats

        Parameters
        ----------
        user : User, optional
            Leave it blank to see your own.
        """
        await interaction.response.defer()
        user = user or interaction.user
        rows = await self.pool.fetchall(
            """
            SELECT
                game_name,
                COUNT(*) FILTER (WHERE win = TRUE) AS wins,
                COUNT(*) FILTER (WHERE win = FALSE) AS losses,
                COUNT(*) AS total_games
            FROM
                singleplayer_games
            WHERE
                user_id = $1
            GROUP BY
                game_name
            ORDER BY
                game_name;
            """,
            user.id,
        )
        embed = self.bot.embed
        embed.title = "Minigame Stats"
        embed.description = f"User: {user.mention}"
        for row in rows:
            embed.add_field(
                name=row["game_name"].capitalize(),
                value=(
                    f"Total games played: `{row['total_games']:04d}`\n"
                    "Wins: `{row['wins']:04d}`\nLosses: `{row['losses']:04d}`"
                ),
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @stats.command(name="wordle", description="View wordle minigame stats")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_wordle(self, interaction: Interaction) -> None:
        """View wordle minigame stats"""
        await self.get_minigame_stats(interaction, "wordle")

    @stats.command(name="letterle", description="View letterle minigame stats")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def minigame_stats_letterle(self, interaction: Interaction) -> None:
        """View letterle minigame stats"""
        await self.get_minigame_stats(interaction, "letterle")

    async def get_minigame_stats(
        self, interaction: Interaction, minigame: str
    ) -> None:
        await interaction.response.defer()
        rows_top = await self.pool.fetchall(
            """
            SELECT
            user_id,
            COUNT(*) FILTER (WHERE win = TRUE) AS wins,
            COUNT(*) FILTER (WHERE win = FALSE) AS losses,
            COUNT(*) AS total_games,
            ROUND(
                (
                    COUNT(*)
                    FILTER (
                        WHERE win = TRUE
                    ) * 100.0 / NULLIF(
                        COUNT(*), 0)
                ),
                2
            ) AS win_percentage
            FROM singleplayer_games
            WHERE game_name = $1
            GROUP BY user_id
            HAVING COUNT(*) >= 5
            ORDER BY win_percentage DESC, total_games DESC
            LIMIT 3
            """,
            minigame,
        )
        rows_bottom = await self.pool.fetchall(
            """
            SELECT
            user_id,
            COUNT(*) FILTER (WHERE win = TRUE) AS wins,
            COUNT(*) FILTER (WHERE win = FALSE) AS losses,
            COUNT(*) AS total_games,
            ROUND(
                (
                    COUNT(*)
                    FILTER (
                        WHERE win = TRUE
                    ) * 100.0 / NULLIF(
                        COUNT(*), 0
                    )
                ),
                2
            ) AS win_percentage
            FROM singleplayer_games
            WHERE game_name = $1
            GROUP BY user_id
            HAVING COUNT(*) >= 5
            ORDER BY win_percentage ASC, total_games DESC
            LIMIT 3
            """,
            minigame,
        )
        embed = self.bot.embed
        embed.title = f"{minigame.capitalize()} Minigame Stats"
        top_players = ""
        for index, row in enumerate(rows_top, 1):
            top_players += (
                f"{index}. <@{row['user_id']}>: `{row['wins']:04d}` wins\n"
            )
        if not top_players:
            top_players = "There is no one here"
        embed.add_field(name=f"Top 3 {minigame} players\n", value=top_players)
        bottom_players = ""
        for index, row in enumerate(rows_bottom, 1):
            bottom_players += (
                f"{index}. <@{row['user_id']}>: `{row['losses']:04d}` losses\n"
            )
        if not bottom_players:
            bottom_players = "No one is here either"
        embed.add_field(
            name=f"Bottom 3 {minigame} players\n",
            value=bottom_players,
            inline=False,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Minigames(bot))
