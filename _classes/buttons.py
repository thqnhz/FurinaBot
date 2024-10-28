from typing import Any

import discord, wavelink
from discord import ButtonStyle, Interaction
from discord.ui import Button
from discord.ext.commands import Bot
from wavelink import Player, Playable

from _classes.embeds import FooterEmbed, ErrorEmbed


class AutoPlayButton(Button):
    """
    Button để thay đổi chế độ auto play ở cuối embed mỗi khi thêm bài mới.
    """
    def __init__(self, autoplay: bool):
        super().__init__()
        if autoplay:
            self.label = "Tắt chế độ phát tự động"
            self.emoji = '❌'
        else:
            self.label = "Bật chế độ phát tự động"
            self.emoji = '✅'

