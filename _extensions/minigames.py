from __future__ import annotations

import ast, asyncio, discord, logging, os
from discord import app_commands, Embed, ButtonStyle
from discord.ext import commands
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from collections import Counter
from io import BytesIO

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


WORDLE_EMOJIS: Dict[str, Dict[WordleLetterStatus, str]]


class Wordle(discord.ui.View):
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    def __init__(self, *, bot: Furina, word: str, owner: discord.User, solo: bool):
        super().__init__(timeout=None)
        self.word = word
        self.bot = bot
        self.owner = owner
        self.solo = solo
        self.attempt: int = 6
        self.embed = Embed(title=f"WORDLE ({len(word)} LETTERS)", description="", color=0x2F3136).set_footer(text="Coded by ThanhZ | v0.2.0-beta")
        self.helped_guess: WordleHelpGuessSelect = WordleHelpGuessSelect()
        self.selected_guess: Optional[str] = None
        self.is_winning = False

        # a list to store the status of the letters in alphabetical order, init with 26 0s
        self.available: List[WordleLetterStatus] = [WordleLetterStatus.UNUSED]*26

        # update the availability right away to get the keyboard field
        self.update_available_characters()

    @property
    def is_over(self) -> bool:
        """Is the game over or not"""
        return self.attempt == 0 or self.is_winning

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
            self.is_winning = True
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
            async with self.bot.cs.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{guess.lower()}") as response:
                if response.status != 200:
                    return await interaction.followup.send(f"`{guess}` is not a real word!", ephemeral=True)
        
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
            if self.is_winning:
                self.embed.color = discord.Color.green()
                button.style = ButtonStyle.success
                button.label = "You WON!"
            else:
                self.embed.color = discord.Color.red()
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
        super().__init__(style=ButtonStyle.secondary, label="Look Up", emoji="\U0001f310", row=0)
        self.word = word

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        view = await Utils.dictionary_call(self.word)
        await interaction.followup.send(embed=view.embeds[0], view=view)


class WordleHelpGuessSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select a helped guess", options=[], min_values=1, max_values=1, row=1)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: Wordle = self.view
        await interaction.response.defer()
        if interaction.user == view.owner:
            view.selected_guess = self.values[0]

class Minigames(commands.GroupCog, group_name="minigame"):
    """Các Minigame bạn có thể chơi"""
    def __init__(self, bot: Furina):
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
        wordle_letters_path = "./wordle_letters"
        filenames = os.listdir(wordle_letters_path)
        total = len(filenames)
        for index, filename in enumerate(filenames, 1):
            emoji = filename.split('.')[0].upper()
            with open(f"{wordle_letters_path}/{filename}", "rb") as file:
                try:
                    print(f"\rUploading {emoji}....................({index:03d}/{total})", end="")
                    await self.bot.create_application_emoji(name=emoji, image=file.read())
                    await asyncio.sleep(0.5)
                except discord.HTTPException:
                    pass
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
                     interaction: discord.Interaction,
                     letters: app_commands.Range[int, 3, 8] = 5,
                     solo: bool = True):
        """
        Wordle minigame

        Parameters
        -----------
        interaction: `discord.Interaction`
            - The interaction object
        letters: `app_commands.Range[int, 3, 8] = 5`
            - Number of letters for this game (3-8), default to 5
        """
        await interaction.response.defer()
        async with self.bot.cs.get(f"https://random-word-api.vercel.app/api?length={letters}") as response:
            word: str = ast.literal_eval(await response.text())[0]
        view = Wordle(bot=self.bot, word=word.upper(), owner=interaction.user, solo=solo)
        await interaction.followup.send(embed=view.embed, view=view)


async def setup(bot: Furina):
    await bot.add_cog(Minigames(bot))