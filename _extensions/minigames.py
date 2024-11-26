import discord, random, string
from discord import Embed, ButtonStyle
from discord.ext import commands
from typing import TYPE_CHECKING, List
from collections import Counter


if TYPE_CHECKING:
    from bot import Furina


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
        self.moves: List[int] = []
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
        

class Wordle(discord.ui.View):
    def __init__(self, word: str):
        super().__init__(timeout=None)
        self.word: str = word
        self.message: discord.Message | None = None
        self.attempt: int = 6
        self.embed = Embed(title="WORDLE", description="").set_footer(text="Coded by ThanhZ")
        self.alphabet: str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        # status dict để kiểm tra xem ký tự có không được dùng(0), không nằm trong đáp án(1), sai vị trí(2)
        # hay đúng vị trí(3)
        self.STATUS: dict[str, int] = {
            'UNUSED':      0,
            'NOT_IN_WORD': 1,
            'WRONG_POS':   2,
            'CORRECT':     3
        }

        # list để lưu trạng thái, bắt đầu bằng 26 số 0
        self.available: List[int] = [self.STATUS['UNUSED']]*26

        # cập nhật trạng thái của các ký tự
        self.update_available_characters()

    def check_guess(self, guess: str):
        """Kiểm tra input từ người dùng."""
        result = [""] * len(self.word)
        word_counter = Counter(self.word)

        # kiểm tra ký tự nằm đúng vị trí (xanh lá)
        for i in range(len(self.word)):
            if guess[i] == self.word[i]:
                result[i] = ":green_square:"
                word_counter[guess[i]] -= 1

                # lấy index của ký tự đúng từ bảng chữ cái sau đó chỉnh sửa trạng thái thành đúng vị trí (3)
                letter_index = self.alphabet.index(guess[i])
                self.available[letter_index] = self.STATUS['CORRECT']
                
        # kiểm tra ký tự nằm sai vị trí (vàng) hoặc không nằm trong đáp án (xám)
        for i in range(len(self.word)):
            # nếu ký tự ở vị trí đó đã là màu xanh thì skip đến vòng lặp kế tiếp
            if result[i] != "":
                continue

            # lấy index của ký tự để chỉnh sửa thành sai vị trí (2) hoặc không nằm trong đáp án (1)
            letter_index = self.alphabet.index(guess[i])
            if guess[i] in word_counter and word_counter[guess[i]] > 0:
                result[i] = ":yellow_square:"
                word_counter[guess[i]] -= 1

                # trạng thái của ký tự có ưu tiên từ xanh lá (3) > vàng (2) > xám (1) > trắng (0)
                # nên nếu ký tự này đã là màu xanh lá (3) từ trước thì không thay đổi từ xanh sang vàng (2)
                if self.available[letter_index] != self.STATUS['CORRECT']:
                    self.available[letter_index] = self.STATUS['WRONG_POS']
            else:
                result[i] = ":black_large_square:"

                # tương tự như độ ưu tiên trên, vì ký tự xám (1) chỉ có thể thay thế ký tự trắng (0)
                # nên phải kiểm tra xem nó có bé hơn ký tự vàng (2) hay không
                if self.available[letter_index] < self.STATUS['WRONG_POS']:
                        self.available[letter_index] = self.STATUS['NOT_IN_WORD']

        self.update_available_characters()
        return "".join(result)

    def update_available_characters(self):
        """Cập nhật trạng thái cho các ký tự."""

        # tạo layout bàn phím để dễ hình dung hơn
        keyboard_layout = [
            'QWERTYUIOP',
            'ASDFGHJKL',
            'ZXCVBNM'
        ]

        available = ""
        tab = 0
        for row in keyboard_layout:
            available += ' '*tab*2 # ký tự trắng để off set bàn phím
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
        self.embed.add_field(name="Bàn phím", value=available)

    @discord.ui.button(label="Đoán", emoji="\U0001f4dd", custom_id="guess_button")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WordleModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        result = self.check_guess(modal.guess)
        self.embed.description += f"`{modal.guess}` {result}\n"
        self.attempt -= 1
        self.remaining_attempt_button.label = f"Còn lại: {self.attempt}"

        # nếu kết quả là 5 ký tự xanh hoặc hết lượt đoán
        if result == (":green_square:" * 5) or self.attempt == 0:
            button.disabled = True
            self.embed.description += f"Đáp án là: `{self.word}`"
            if result == (":green_square:" * 5):
                button.style = ButtonStyle.success
                button.label = "Bạn đã đoán đúng"
            else:
                button.style = ButtonStyle.danger
                button.label = "Bạn đã thua"
        await self.message.edit(embed=self.embed, view=self)

    @discord.ui.button(label="Còn lại: 6", emoji="\U0001f4ad", custom_id="remaining_attempt", disabled=True)
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
        self.guess = self.text_input.value.upper()


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
    async def keo_bua_bao(self, ctx: commands.Context):
        view: RockPaperScissor = RockPaperScissor()
        view.message = await ctx.reply(embed=view.embed, view=view)

    @commands.hybrid_command(name='wordle', description="Wordle minigame")
    async def wordle(self, ctx: commands.Context):
        word: str = random.choice(self.words)
        while len(word) != 5 or any(char not in string.ascii_letters for char in word):
            word = random.choice(self.words)
        view = Wordle(word.upper())
        view.message = await ctx.reply(embed=view.embed, view=view)


async def setup(bot: "Furina"):
    await bot.add_cog(Minigames(bot))

