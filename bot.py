import discord, platform, nltk
from discord import Intents, Activity, ActivityType
from discord.ext.commands import Bot, when_mentioned_or
from nltk.corpus import wordnet
from typing import List
from wavelink import Node, Pool


from settings import *
from _classes.embeds import FooterEmbed


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

    async def refresh_node_connection(self):
        self.node = Node(uri=LAVA_URI, password=LAVA_PW, heartbeat=5.0, retries=1)
        await Pool.close()
        await Pool.connect(client=self, nodes=[self.node])

    async def on_ready(self) -> None:
        print(PRFX + " Đã đăng nhập bằng " + Fore.BLUE + self.user.name)
        print(PRFX + " Discordpy version " + Fore.BLUE + discord.__version__)
        print(PRFX + " Python version " + Fore.BLUE + str(platform.python_version()))

        channel = self.get_channel(DEBUG_CHANNEL)
        embed = FooterEmbed(title="Bot hoàn tất khởi động và sẵn sàng nhận lệnh!")
        await channel.send(embed=embed)

    async def setup_hook(self) -> None:
        nltk.download("wordnet")
        self.words: List[str] = list(wordnet.words())
        
        for filename in os.listdir("./_extensions"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"_extensions.{filename[:-3]}")
                    print(PRFX + " Đã load extension: " + Fore.BLUE + str(filename[:-3]))
                except Exception as e:
                    print(PRFX + " Lỗi khi load extension " + Fore.BLUE + str(filename[:-3]) + f"{e}")

