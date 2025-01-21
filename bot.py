import asqlite, aiohttp, datetime, discord, os, platform, nltk, wavelink
from discord import Intents, Activity, ActivityType, Embed, app_commands
from discord.ext.commands import Bot, when_mentioned_or
from nltk.corpus import wordnet
from typing import List

from settings import DEFAULT_PREFIX, ACTIVITY_NAME, DEBUG_WEBHOOK

class Furina(Bot):
    def __init__(self, *, pool: asqlite.Pool, client_session: aiohttp.ClientSession) -> None:
        super().__init__(
            command_prefix     = self.get_pre,
            case_insensitive   = True,
            strip_after_prefix = True,
            intents            = Intents.all(),
            help_command       = None,
            activity           = Activity(type=ActivityType.playing,
                                          name=ACTIVITY_NAME,
                                          state="Playing: N̸o̸t̸h̸i̸n̸g̸")
        )

        # only allow app_commands to be used in servers, so you can't use the bot's app_commands in its dm
        # change the aguments or comment this out if you wish to use app_commands in bot's dm
        self.tree.allowed_contexts = app_commands.AppCommandContext(dm_channel=False, guild=True)

        # database pool
        self.pool = pool

        # client session for requests
        self.cs = client_session

    async def create_prefix_table(self) -> None:
        async with self.pool.acquire() as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS custom_prefixes
                   ( guild_id INT NOT NULL PRIMARY KEY, prefix TEXT NOT NULL )""")
            
    async def update_prefixes(self) -> None:
        async with self.pool.acquire() as db:
            async with db.execute("""SELECT * FROM custom_prefixes""") as cursor:
                prefixes = await cursor.fetchall()
                self.prefixes = {prefix[0]: prefix[1] for prefix in prefixes}
            
    def get_pre(self, _, message: discord.Message) -> List[str]:
        prefix = self.prefixes.get(message.guild.id) or DEFAULT_PREFIX
        return when_mentioned_or(prefix)(self, message)

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user.name}")
        print(f"discord.py version {discord.__version__}")
        print(f"Wavelink version {wavelink.__version__}")
        print(f"Python version {platform.python_version()}")

        try:
            embed = Embed(color=self.user.accent_color).set_author(
                name="BOT IS READY!",
                icon_url=self.user.display_avatar.url
            )
            embed.timestamp = datetime.datetime.now()
            discord.SyncWebhook.from_url(DEBUG_WEBHOOK).send(embed=embed)
        except ValueError:
            print("Cannot get the Webhook url for on_ready events."
                  "If you don't want to get a webhook message when the bot is ready, please ignore this.")

    async def setup_hook(self) -> None:
        await self.create_prefix_table()
        await self.update_prefixes()

        nltk.download("wordnet")
        self.words: List[str] = list(wordnet.words())
        
        for filename in os.listdir("./_extensions"):
            if filename.endswith(".py"):
                extension = filename[:-3]
                try:
                    await self.load_extension(f"_extensions.{extension}")
                    print(f"Loaded extension: {extension}")
                except discord.ext.commands.errors.NoEntryPointError:
                    print(f"Extension {extension} has no setup function so it cannot be loaded.")
                except Exception as e:
                    print(f"An error occured when trying to load {extension}\n{e}")

