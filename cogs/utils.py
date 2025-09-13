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

import datetime
import inspect
import io
import pathlib
import platform
import re
from enum import Enum
from time import perf_counter
from typing import TYPE_CHECKING

import dateparser
import discord
import docstring_parser
import psutil
from discord import Interaction, Member, app_commands, ui
from discord.ext import commands
from discord.ui import Select

from core import FurinaBot, FurinaCog, FurinaCtx, settings, utils as utils
from core.views import Container, LayoutView

if TYPE_CHECKING:
    from core import FurinaBot


class HelpActionRow(ui.ActionRow):
    def __init__(self, *, bot: FurinaBot) -> None:
        super().__init__(HelpSelect(bot))


class HelpSelect(Select):
    """Help Selection Menu"""

    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(
            placeholder="Select a category for command list",
            options=[
                discord.SelectOption(label=cog_name, description=cog.__doc__)
                for cog_name, cog in bot.cogs.items()
                if cog.__cog_commands__ and cog_name not in ["Hidden", "Jishaku"]
            ],
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        container = Utils.list_cog_commands(
            cog=self.bot.get_cog(self.values[0]),
            bot_prefix=self.bot.prefixes.get(interaction.guild.id) or settings.DEFAULT_PREFIX,
        )
        container.add_item(ui.Separator()).add_item(HelpActionRow(bot=self.bot))
        view = LayoutView(container)
        view.message = self.view.message
        self.view.message = None
        await interaction.response.edit_message(view=view)


class MemberStatus(Enum):
    online = ":green_circle: `Online`"
    offline = ":black_circle: `Offline`"
    idle = ":yellow_circle: `Idling`"
    dnd = ":red_circle: `Do Not Disturb`"


class Utils(FurinaCog):
    """Utility Commands"""

    async def cog_load(self) -> None:
        await self.__update_custom_prefixes()
        return await super().cog_load()

    async def __update_custom_prefixes(self) -> None:
        """Fetch and update custom prefixes"""
        prefixes = await self.pool.fetchall("""SELECT * FROM custom_prefixes""")
        self.bot.prefixes = {prefix["guild_id"]: prefix["prefix"] for prefix in prefixes}

    @staticmethod
    def list_cog_commands(*, cog: FurinaCog, bot_prefix: str) -> Container:
        content: str = f"## {cog.__cog_name__} Commands\n"
        prefix: str = ""
        for command in cog.walk_commands():
            if command.hidden:
                continue
            doc = docstring_parser.parse(command.callback.__doc__ or "No description")
            prefix += f"- **{bot_prefix}{command.qualified_name}:** `{doc.short_description}`\n"

        if prefix:
            content += "### Prefix commands\n" + prefix

        slash: str = ""
        for command in cog.walk_app_commands():
            if isinstance(command, app_commands.Group):
                continue
            doc = docstring_parser.parse(command.callback.__doc__ or "No description")
            slash += f"- **{command.qualified_name}:** `{doc.short_description}`\n"

        if slash:
            content += "### Slash commands\n" + slash

        if not prefix and not slash:
            content += "This cog has no commands to show"

        return Container(ui.TextDisplay(content))

    @FurinaCog.listener("on_message")
    async def on_mention(self, message: discord.Message) -> None:
        """Sends a container with some info and help select menu when mentioned"""
        bot = self.bot
        if message.author.bot:
            return

        if message.content == bot.user.mention:
            prefix = bot.prefixes.get(message.guild.id) or bot.DEFAULT_PREFIX
            header_section = ui.Section(
                "## Miss me that much?\n"
                f"My prefix is `{prefix}`\n"
                f"You can also do {bot.user.mention}` <command> `\n"
                "I am also supporting *slash commands*\n"
                "Type `/` to see what i can do!",
                accessory=ui.Thumbnail(bot.user.display_avatar.url),
            )
            source_section = ui.Section(
                "### I am also open source",
                accessory=ui.Button(
                    label="Click me to view source code",
                    style=discord.ButtonStyle.link,
                    url=r"https://github.com/thqnhz/furinabot/tree/master",
                ),
            )
            bot_latency: str = f"{round(bot.latency * 1000, 2)}ms"
            time = perf_counter()
            await self.pool.fetchone("""SELECT * FROM custom_prefixes LIMIT 1""")
            db_latency = f"{round((perf_counter() - time) * 1000, 2)}ms"
            more_info = ui.TextDisplay(
                "### More info\n"
                f"- **Uptime:** `{bot.uptime}`\n"
                f"- **Bot Latency:** `{bot_latency}`\n"
                f"- **Database Latency:** `{db_latency}`"
            )
            container = Container(
                header_section,
                ui.Separator(),
                source_section,
                ui.Separator(),
                more_info,
                ui.Separator(),
                HelpActionRow(bot=bot),
            )
            view = LayoutView(container)
            view.message = await message.reply(view=view)

    @commands.command(name="ping")
    async def ping_command(self, ctx: FurinaCtx) -> None:
        """Get the bot's pings

        Get latencies of bot to Discord server, to Voice server and to Database.
        For voice, `-1ms` means it is not connected to any voice channels.
        For lavalink node:
        - :white_check_mark: means it is connected.
        - :arrows_clockwise: means it is still trying to connect (maybe the password is wrong).
        - :negative_squared_cross_mark: means it is disconnected.
        """
        bot_latency: float = self.bot.latency
        voice_latency: float | int = (
            await self.bot.lavalink.nodes[0].get_rest_latency() if ctx.guild.voice_client else -1
        )
        db_latency: float = await self.db_ping()
        container = Container(
            ui.TextDisplay("## Pong!"),
            ui.Separator(),
            ui.TextDisplay(
                f"**Bot Latency:** `{bot_latency * 1000:.2f}ms`\n"
                f"**Voice Latency:** `{voice_latency:.2f}ms`\n"
                f"**Database Latency:** `{db_latency * 1000:.2f}ms`"
            ),
        ).add_footer()
        await ctx.reply(view=LayoutView(container))

    async def db_ping(self) -> float:
        """|coro|

        Ping the database

        Returns
        -------
        :class:`float`
            The time it takes for the database to respond
        """
        time = perf_counter()
        await self.pool.execute("""SELECT * FROM custom_prefixes LIMIT 1""")
        return perf_counter() - time

    @commands.command(name="prefix")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_command(self, ctx: FurinaCtx, prefix: str) -> None:
        """Set the bot prefix

        Can only be used by member with `Manage Server` permission.
        Can **not** be used in DM.
        New prefix cannot be more than 3 characters long.
        Quotation marks *will be cleared*! So `"a."` ~ `a.`
        Set the prefix to either: `clear`, `reset`, `default`, will reset to the default prefix `!`

        Parameters
        ----------
        prefix : str
            The new prefix
        """
        prefix = prefix.strip("'\" ")
        if len(prefix) > 3 or not prefix:
            await ctx.reply(
                view=LayoutView(Container(ui.TextDisplay(f"{settings.CROSS} **Invalid prefix**")))
            )
            return

        if prefix in ["clear", "reset", "default", settings.DEFAULT_PREFIX]:
            await self.pool.execute(
                """
                DELETE FROM custom_prefixes WHERE guild_id = ?
                """,
                ctx.guild.id,
            )
        else:
            await self.pool.execute(
                """
                INSERT OR REPLACE INTO custom_prefixes (guild_id, prefix) VALUES (?, ?)
                """,
                ctx.guild.id,
                prefix,
            )
        await self.__update_custom_prefixes()
        prefix = self.bot.prefixes.get(ctx.guild.id) or settings.DEFAULT_PREFIX
        await ctx.reply(
            view=LayoutView(
                Container(ui.TextDisplay(f"{settings.CHECKMARK} **Prefix set to** `{prefix}`"))
            )
        )

    @commands.command(name="source", aliases=["src"])
    async def source_command(self, ctx: FurinaCtx, *, command: str | None = "") -> None:
        """Get the bot source code

        Get the source code of the bot or a specific command.
        Return a github link to the bot if no command is provided.
        Otherwise return the command source code.

        Parameters
        ----------
        command : str, optional
            The command of which you need the source code
        """
        cmd: commands.Command | None = self.bot.get_command(command.lower())
        file: discord.File | None = None
        git: str = r"https://github.com/thqnhz/FurinaBot/tree/master"
        if not command:
            res = git
        elif not cmd:
            res = f"No commands named {command.lower()}"
        else:
            source: str = inspect.getsource(cmd.callback)
            lines, start_line = inspect.getsourcelines(cmd.callback)
            end_line = start_line + len(lines) - 1
            src_file = inspect.getfile(cmd.callback)
            path = pathlib.Path(src_file).resolve().relative_to(pathlib.Path.cwd())
            if len(source) >= 1000:
                res = "Source code is too long so I will send a file instead\n"
                file = discord.File(
                    io.BytesIO(source.encode("utf-8")), filename=f"{cmd.qualified_name}.py"
                )
            else:
                res = f"```py\n{source}\n```"
            git = f"<{git}/{path}#L{start_line}-L{end_line}>"
            res += f"\nHere is the corresponding git link: {git}"
        await ctx.reply(res, file=file)

    @commands.command(name="help")
    async def help_command(self, ctx: FurinaCtx, *, query: str | None = None) -> None:
        """The help command

        Use `help <category>` to get the category commands.
        Use `help <command>` to get the command help.
        Otherwise, shows the list of categories.

        Parameters
        ----------
        query : str, optional
            Category/Command name you need help with
        """
        # !help
        if query is None:
            prefix = self.bot.prefixes.get(ctx.guild.id) or settings.DEFAULT_PREFIX
            header = ui.Section(
                f"## {self.bot.user.mention} Help Command\n"
                "### To get help with a category\n"
                f"- Use `{prefix}help <category>`\n"
                "### To get help with a command\n"
                f"- Use `{prefix}help <command>`",
                accessory=ui.Thumbnail(self.bot.user.display_avatar.url),
            )
            container = Container(header, ui.Separator(), HelpActionRow(bot=self.bot)).add_footer()
            view = LayoutView(container)
            view.message = await ctx.reply(view=view)
            return

        # !help <CogName>
        cog: FurinaCog | None = None
        for cog_ in self.bot.cogs:
            if cog_.lower() == query.lower():
                cog = self.bot.get_cog(cog_)
                break
        if cog and cog.__cog_name__ not in ["Hidden", "Jishaku"]:
            container = self.list_cog_commands(
                cog=cog, bot_prefix=ctx.prefix or self.bot.DEFAULT_PREFIX
            )
            container.add_item(ui.Separator()).add_item(HelpActionRow(bot=self.bot))
            view = LayoutView(container)
            view.message = await ctx.reply(view=view)
            return

        # !help <Command>
        command = self.bot.get_command(query.lower())
        if command and not command.hidden and command.name != "jishaku":
            doc = docstring_parser.parse(command.callback.__doc__)
            usage = command.qualified_name
            syntax = ""
            for param in doc.params:
                # usage is
                # command <required> [optional]  # noqa: ERA001
                optional: bool = param.is_optional
                usage += f" {'[' if optional else '<'}{param.arg_name}{']' if optional else '>'}"
                # syntax is
                # param_name : `param_type = default_value`
                #     param description
                syntax += f"\n{param.arg_name}: {param.type_name}\n"
                syntax += f"    - {param.description}\n"

            container = Container(
                ui.TextDisplay(f"##  {usage} \n" + doc.short_description),
                ui.Separator(),
                ui.TextDisplay(doc.long_description),
            )
            if syntax:
                container.add_item(ui.Separator()).add_item(
                    ui.TextDisplay(f"**Syntax:** ```py\n{syntax}```")
                )

            aliases = (
                "**Alias(es):** " + ", ".join(alias for alias in command.aliases)
                if command.aliases
                else ""
            )

            if aliases:
                container.add_item(ui.Separator()).add_item(ui.TextDisplay(aliases))

            await ctx.reply(view=LayoutView(container))
        else:
            raise commands.BadArgument("""I don't recognize that command/category""")

    @commands.command(name="vps", hidden=True)
    @commands.is_owner()
    async def vps_command(self, ctx: FurinaCtx) -> None:
        """Get VPS Info"""
        # OS Version
        os_version = platform.platform()

        # CPU Usage
        cpu_percent = psutil.cpu_percent()

        # RAM Usage
        memory_info = psutil.virtual_memory()
        ram_total = round(memory_info.total / (1024**3), 2)
        ram_used = round(memory_info.used / (1024**3), 2)
        ram_available = round(memory_info.available / (1024**3), 2)
        ram_cached = round(ram_total - ram_used - ram_available, 2)

        # Disk Usage
        disk_info = psutil.disk_usage("./")
        disk_total = round(disk_info.total / (1024**3), 2)
        disk_used = round(disk_info.used / (1024**3), 2)
        disk_available = round(disk_info.free / (1024**3), 2)

        embed = self.embed
        embed.title = "VPS Info"
        embed.add_field(name="Operating System", value=os_version)
        embed.add_field(name="CPU Usage", value=f"{cpu_percent}%", inline=False)
        embed.add_field(
            name="RAM Usage",
            value=f"- Total: {ram_total}GB\n"
            f"- Used: {ram_used}GB\n"
            f"- Cache: {ram_cached}GB\n"
            f"- Free: {ram_available}GB",
            inline=False,
        )
        embed.add_field(
            name="Disk Usage",
            value=f"- Total: {disk_total}GB\n- Used: {disk_used}GB\n- Free: {disk_available}GB",
            inline=False,
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="userinfo", aliases=["uinfo", "whois"])
    async def user_info_command(self, ctx: FurinaCtx, member: Member | None = None) -> None:
        """Get the user's info

        Shows info about the member, including their name, id, status, roles,...
        Shows your info if no member is provided.

        Parameters
        ----------
        member : Member, optional
            The member to get info from
        """
        member = ctx.guild.get_member(member.id if member else ctx.author.id)
        header = ui.Section(
            ui.TextDisplay(
                f"## {member.display_name}"
                + (" (Bot)\n" if member.bot else "\n")
                + f"**Username:** `{member}`\n"
                f"**ID:** `{member.id}`\n"
                f"**Status:** {MemberStatus[str(member.status)].value}"
            ),
            accessory=ui.Thumbnail(member.display_avatar.url),
        )
        account_created = int(member.created_at.timestamp())
        server_joined = int(member.joined_at.timestamp())
        role_list = ", ".join(
            role.name for role in reversed(member.roles) if role.name != "@everyone"
        )
        container = Container(
            header,
            ui.Separator(),
            ui.TextDisplay(
                f"**Account Created:** <t:{account_created}> or <t:{account_created}:R>\n"
                f"**Server Joined:** <t:{server_joined}> or <t:{server_joined}:R>"
                f"**Roles ({len(member.roles) - 1}):** ```\n{role_list}\n```"
            ),
        )
        if member.activities:
            container.add_item(ui.Separator())
            activities = "**Activities:**\n"
            for i, activity in enumerate(member.activities, 1):
                activities += f"{i}. **{activity.type.name.capitalize()}"
                activities += f"{':** ' + activity.name if activity.name else '**'}\n"
            container.add_item(ui.TextDisplay(activities))
        await ctx.reply(view=LayoutView(container))

    @commands.hybrid_command(name="dictionary", aliases=["dict"])
    @app_commands.allowed_installs(guilds=True, users=True)
    async def dict_command(self, ctx: FurinaCtx, word: str) -> None:
        """Lookup a word in the dictionary

        Use DictionaryAPI to look up a word.
        Note that it can only look up the first word, every other words after will be ignored.

        Parameters
        ----------
        word : str
            The word to look up
        """
        view = await utils.call_dictionary(word.split(maxsplit=1)[0], self.cs)
        view.message = await ctx.reply(view=view)

    @commands.command(name="wordoftheday", aliases=["wotd"])
    async def wotd_command(self, ctx: FurinaCtx, *, date: str | None = None) -> None:
        """View today's word

        Shows today's, or any day's word of the day.
        Can take any date format, even human friendly ones.
        Like 'yesterday', 'last month',...

        Parameters
        ----------
        date : str, optional
            The date to get word of the day from
        """
        date_ = dateparser.parse(
            date or datetime.datetime.now(tz=datetime.timezone.utc).strftime(r"%Y-%m-%d"),
            settings={"TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True},
        )
        date = date_.strftime(r"%Y-%m-%d")
        day_check = r"202\d-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"
        if not re.match(day_check, date):
            await ctx.reply("You entered a very old date, try a newer one")
            return
        ddmmyyyy = date_.strftime(r"%A %d/%m/%Y")
        api_link = f"https://api.wordnik.com/v4/words.json/wordOfTheDay?date={date}&api_key={settings.WORDNIK_API}"
        async with self.bot.cs.get(api_link) as response:
            if response.status != 200:
                await ctx.reply("Something went wrong")
                return
            content: dict = await response.json()
        container = ui.Container(
            ui.TextDisplay(f"## {content['word']} ({content['definitions'][0]['partOfSpeech']})"),
            ui.TextDisplay("**Definition:**\n>>> " + content["definitions"][0]["text"]),
            ui.Separator(),
            ui.TextDisplay("**Fun fact:**\n" + content["note"]),
            ui.TextDisplay(f"-# Coded by ThanhZ | Date: `{ddmmyyyy}`"),
        )
        await ctx.reply(view=LayoutView().add_item(container))

    @commands.command(name="stats", aliases=["stat"])
    async def stats_command(self, ctx: FurinaCtx) -> None:
        """Get the bot's stats

        Get:
        - The bot's uptime.
        - Number of servers the bot is in.
        - Number of prefix commands have been completed.
        - Most recent 10 prefix commands.
        - Number of slash commands have been completed.
        - Most recent 10 slash commands.
        """
        container = self.container.add_item(
            ui.TextDisplay(f"## {self.bot.user.display_name} Stats"),
            ui.Separator(),
            ui.TextDisplay(f"### Uptime: {self.bot.uptime}### Servers: {len(self.bot.guilds)}"),
            ui.Separator(),
        )
        guild_id = ctx.guild.id
        prefix_cmds = ""
        if guild_id in self.bot.command_cache:
            prefix_cmds = self.bot.command_cache[guild_id]
        if prefix_cmds:
            prefix_cmds = "- " + "\n- ".join(prefix_cmds)
        else:
            prefix_cmds = "No prefix commands history from this server"
        app_cmds = ""
        if guild_id in self.bot.app_command_cache:
            app_cmds = self.bot.app_command_cache[guild_id]
        if app_cmds:
            app_cmds = "- " + "\n- ".join(app_cmds)
        else:
            app_cmds = "No app commands history from this server"
        total_prefix = await self.pool.fetchval("""SELECT COUNT(*) FROM prefix_commands""")
        total_slash = await self.pool.fetchval("""SELECT COUNT(*) FROM app_commands""")
        container.add_item(
            ui.TextDisplay(
                "### Most recent prefix commands\n"
                + prefix_cmds
                + "\n"
                + f"### Total prefix commands completed: {total_prefix}\n"
                + "### Most recent slash commands\n"
                + app_cmds
                + "\n"
                + f"### Total slash commands completed: {total_slash}\n"
            )
        )
        await ctx.reply(view=LayoutView(container))


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Utils(bot))
