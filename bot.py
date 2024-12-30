import datetime, discord, os, platform, nltk, wavelink
from discord import Intents, Activity, ActivityType, Embed, app_commands
from discord.ext.commands import Bot, when_mentioned_or
from nltk.corpus import wordnet
from typing import List

from settings import PREFIX, ACTIVITY_NAME, DEBUG_WEBHOOK

class Furina(Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix     = when_mentioned_or(PREFIX),
            case_insensitive   = True,
            strip_after_prefix = True,
            intents            = Intents.all(),
            help_command       = None,
            activity           = Activity(type=ActivityType.playing,
                                          name=ACTIVITY_NAME,
                                          state="Playing: N̸o̸t̸h̸i̸n̸g̸")
        )
        self.tree.allowed_contexts = app_commands.AppCommandContext(dm_channel=False, guild=True)

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user.name}")
        print(f"discord.py version {discord.__version__}")
        print(f"Wavelink version {wavelink.__version__}")
        print(f"Python version {platform.python_version()}")

        embed = Embed(color=self.user.accent_color).set_author(
            name="BOT IS READY!",
            icon_url=self.user.display_avatar.url
        )
        embed.timestamp = datetime.datetime.now()
        discord.SyncWebhook.from_url(DEBUG_WEBHOOK).send(embed=embed)

    async def setup_hook(self) -> None:
        nltk.download("wordnet")
        self.words: List[str] = list(wordnet.words())
        
        for filename in os.listdir("./_extensions"):
            if filename.endswith(".py"):
                extension = filename[:-3]
                try:
                    await self.load_extension(f"_extensions.{extension}")
                    print(f"Đã load extension: {extension}")
                except Exception as e:
                    print(f"Lỗi khi load extension {extension}\n{e}")

