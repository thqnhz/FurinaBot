from __future__ import annotations

import platform
import psutil
from enum import Enum
from time import perf_counter
from typing import TYPE_CHECKING, Dict, Optional

import aiohttp
import discord
from discord import app_commands, Color, Embed
from discord.ext import commands
from discord.ui import Select
from wavelink import NodeStatus, Pool

from furina import FurinaCog, FurinaCtx
from settings import *
from cogs.utility.views import PaginatedView, View
from cogs.utility.sql import PrefixSQL


if TYPE_CHECKING:
    from furina import FurinaBot


class HelpSelect(Select):
    """Help Selection Menu"""
    def __init__(self, bot: FurinaBot):
        super().__init__(
            placeholder="Select a category for command list",
            options=[
                discord.SelectOption(
                    label=cog_name, description=cog.__doc__
                ) for cog_name, cog in bot.cogs.items() if cog.__cog_commands__ and cog_name not in ['Hidden', 'Jishaku']
            ]
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = Utils.command_list_embed(
            cog=self.bot.get_cog(self.values[0]),
            prefix=self.bot.prefixes.get(interaction.guild.id) or DEFAULT_PREFIX,
            embed=self.bot.embed
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class MemberStatus(Enum):
    online  = ":green_circle: `Online`"
    offline = ":black_circle: `Offline`"
    idle    = ":yellow_circle: `Idling`"
    dnd     = ":red_circle: `DND`"
    

NODE_STATUSES: Dict[NodeStatus, str] = {
    NodeStatus.CONNECTED: ":white_check_mark:",
    NodeStatus.CONNECTING: ":arrows_clockwise:",
    NodeStatus.DISCONNECTED: ":negative_squared_cross_mark:"
}


class Utils(FurinaCog):
    """Utility Commands"""
    @property
    def embed(self) -> Embed:
        return self.bot.embed
    
    @staticmethod
    def command_list_embed(*, cog: FurinaCog, prefix: str, embed: Embed) -> Embed:
        embed.title = cog.__cog_name__
        embed.description = "\n".join(
            f"- **{prefix}{command.qualified_name}:** `{command.description}`"
            for command in cog.walk_commands()
        )
        return embed

    @FurinaCog.listener("on_message")
    async def on_mention(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if message.content == self.bot.user.mention:
            embed = self.embed
            embed.description = self.bot.application.description
            embed.color = Color.blue()
            embed.set_author(
                name="Miss me that much?",
                icon_url="https://cdn.7tv.app/emote/01HHV72FBG000870SVK5KGTSJM/4x.png"
            )
            embed.add_field(name=f"My prefix is `{self.bot.prefixes.get(message.guild.id) or DEFAULT_PREFIX}`",
                            value=f"You can also mention me\n{self.bot.user.mention}` <command> `")
            embed.add_field(name="I am also open source", value="[**My repository**](https://github.com/Th4nhZ/FurinaBot/tree/master)")
            uptime_td = discord.utils.utcnow() - self.bot.uptime
            uptime: str = f"{uptime_td.days}d {uptime_td.seconds // 3600}h {(uptime_td.seconds // 60) % 60}m"
            api_ping: str = f"{round(self.bot.latency * 1000)}ms"
            time = perf_counter()
            await self.bot.pool.execute("""SELECT 1""")
            db_ping = f"{round((perf_counter() - time) * 1000)}ms"
            embed.add_field(name="More info", 
                            value=f"Uptime: `{uptime}`\nAPI Ping: `{api_ping}`\nDatabase Ping: `{db_ping}`")
            embed.timestamp = message.created_at
            view = View().add_item(HelpSelect(self.bot))
            view.message = await message.channel.send(embed=embed, view=view, reference=message)

    @commands.command(name='ping', description="Get the ping to discord api and lavalink nodes")
    async def ping_command(self, ctx: FurinaCtx):
        await ctx.defer()
        bot_latency = self.bot.latency
        voice_latency = ctx.guild.voice_client.ping if ctx.guild.voice_client else -1
        time = perf_counter()
        await self.bot.pool.execute("""SELECT 1""")
        db_latency = perf_counter() - time

        embed = self.embed
        embed.title = "Pong!"
        embed.add_field(name="Ping:", value=f"**Text:** {bot_latency * 1000:.2f}ms\n**Voice:** {voice_latency}ms\n**Database:** {db_latency * 1000:.2f}ms")

        for i, node in enumerate(Pool.nodes, 1):
            node_ = Pool.get_node(node)
            node_status = NODE_STATUSES[node_.status]
            embed.add_field(name=f"Node {i}: {node_status}", value="", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="prefix", description="Set a custom prefix for your server")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_command(self, ctx: FurinaCtx, prefix: str):
        await ctx.tick()
        if prefix in ['clear', 'reset', 'default', DEFAULT_PREFIX]:
            await PrefixSQL(pool=self.bot.pool).delete_custom_prefix(guild_id=ctx.guild.id)
        else:
            await PrefixSQL(pool=self.bot.pool).set_custom_prefix(guild_id=ctx.guild.id, prefix=prefix)
        await self.bot.update_prefixes()
        embed = ctx.embed
        embed.description = f"Prefix for this server has been changed to `{self.bot.prefixes.get(ctx.guild.id) or DEFAULT_PREFIX}`"
        await ctx.reply(embed=embed)

    @commands.command(name='source', aliases=['sources', 'src'], description="Source code of the bot")
    async def source_command(self, ctx: FurinaCtx):
        await ctx.reply("https://github.com/Th4nhZ/FurinaBot")

    @commands.command(name='help', description="Help command")
    async def help_command(self, ctx: FurinaCtx, *, category_or_command_name: str = None):
        """
        Parameters
        -----------
        category_or_command_name: `str`
            Category/Command name you need help with
        """
        # !help
        if category_or_command_name is None:
            view = View().add_item(HelpSelect(self.bot))
            view.message = await ctx.reply(view=view)
            return
        
        # !help <CogName>
        cog: FurinaCog = None
        for cog_ in self.bot.cogs.keys():
            if cog_.lower() == category_or_command_name.lower():
                cog = self.bot.get_cog(cog_)
                break
        if cog and cog.__cog_name__ not in ['Hidden', 'Jishaku']:
            embed = self.command_list_embed(cog=cog, prefix=ctx.prefix, embed=self.embed)
            return await ctx.reply(embed=embed)
        
        # !help <Command>
        command = self.bot.get_command(category_or_command_name.lower())
        if command and not command.hidden and command.name != 'jishaku':
            embed = self.embed
            embed.description = (f"- **__Name:__** `{command.qualified_name}`\n"
                                 f"- **__Description:__** {command.description}\n"
                                 f"- **__How to use:__** `{ctx.prefix}{command.qualified_name} {command.signature}`")
            embed.set_footer(text="Aliases: " + ", ".join(alias for alias in command.aliases) if command.aliases else "")
            await ctx.reply(embed=embed)
        else:
            raise commands.BadArgument("""I don't recognize that command/category""")

    @commands.command(name='vps', hidden=True, description="VPS Info")
    @commands.is_owner()
    async def vps_command(self, ctx: FurinaCtx):
        # OS Version
        os_version = platform.platform()

        # CPU Usage
        cpu_percent = psutil.cpu_percent()

        # RAM Usage
        memory_info = psutil.virtual_memory()
        ram_total = round(memory_info.total / (1024 ** 3), 2)
        ram_used = round(memory_info.used / (1024 ** 3), 2)
        ram_available = round(memory_info.available / (1024 ** 3), 2)
        ram_cached = round(ram_total - ram_used - ram_available, 2)

        # Disk Usage
        disk_info = psutil.disk_usage('/')
        disk_total = round(disk_info.total / (1024 ** 3), 2)
        disk_used = round(disk_info.used / (1024 ** 3), 2)
        disk_available = round(disk_info.free / (1024 ** 3), 2)

        embed = self.embed
        embed.title = "VPS Info"
        embed.add_field(name="Operating System", value=os_version)
        embed.add_field(name="CPU Usage", value=f"{cpu_percent}%", inline=False)
        embed.add_field(
            name="RAM Usage",
            value=f'- Total: {ram_total}GB\n'
                  f'- Used: {ram_used}GB\n'
                  f'- Cache: {ram_cached}GB\n'
                  f'- Free: {ram_available}GB',
            inline=False
        )
        embed.add_field(
            name="Disk Usage",
            value=f'- Total: {disk_total}GB\n'
                  f'- Used: {disk_used}GB\n'
                  f'- Free: {disk_available}GB',
            inline=False
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='userinfo', aliases=['uinfo', 'whois'], description="Get info about a member")
    async def user_info_command(self, ctx: FurinaCtx, member: Optional[discord.Member] = None):
        """
        Parameters
        -----------
        member: `Optional[discord.Member]`
            A member to get info from
        """
        member = ctx.guild.get_member(member.id if member else ctx.author.id)
        embed = self.embed
        embed.title = "Member Info"
        embed.color = Color.blue()
        embed.add_field(name="Display Name:", value=member.mention)
        embed.add_field(name="Username:", value=member)
        embed.add_field(name="ID:", value=member.id)
        embed.set_thumbnail(url=member.display_avatar.url)
        account_created = int(member.created_at.timestamp())
        embed.add_field(name="Account Created:", value=f"<t:{account_created}>\n<t:{account_created}:R>")
        server_joined = int(member.joined_at.timestamp())
        embed.add_field(name="Server Joined:", value=f"<t:{server_joined}>\n<t:{server_joined}:R>")
        embed.add_field(name="Status: ", value=MemberStatus[str(member.status)].value)
        embed.add_field(name="Roles:", value=", ".join(role.mention for role in reversed(member.roles) if role.name != '@everyone'))
        if member.activity:
            embed.add_field(
                name="Activity:",
                value=f"**{str.capitalize(member.activity.type.name)}**: `{member.activity.name}`"
                if member.activity.name != None else "`None`"
            )
        embed.timestamp = ctx.message.created_at
        await ctx.reply(embed=embed)

    @staticmethod
    async def dictionary_call(word: str) -> PaginatedView:
        """
        Calls the dictionaryapi

        Parameters
        -----------
        `word: str`
            - The word

        Returns
        -----------
        `PaginatedView`
            A view that contains list of embeds and navigate buttons
        """
        embeds: list[Embed] = []
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as response:
                if response.status == 404:
                    embed = Embed(
                        title=word.capitalize(),
                        description="No definitions found. API call returned 404."
                    ).set_footer(text="Coded by ThanhZ")
                    return PaginatedView(timeout=300, embeds=[embed])
                data: list[dict] = eval(await response.text())

        embed = Embed(title=word.capitalize()).set_footer(text="Coded by ThanhZ")

        for d in data:
            phonetics = d['phonetic'] if 'phonetic' in d \
                else ", ".join([p['text'] for p in d['phonetics'] if 'text' in p])
            # Phiên âm
            embed.description = f"Pronunciation: `{phonetics}`"

            # Định nghĩa
            for meaning in d['meanings']:
                embed.title += f" ({meaning['partOfSpeech']})"
                if meaning['synonyms']:
                    embed.add_field(
                        name="Synonyms:",
                        value=', '.join(meaning['synonyms'])
                    )
                if meaning['antonyms']:
                    embed.add_field(
                        name="Antonyms:",
                        value=', '.join(meaning['antonyms'])
                    )
                definition_value = ""
                for definition in meaning['definitions']:
                    after = definition_value + ("\n- " + definition['definition'])
                    if len(after) < 1024:
                        definition_value = after
                embed.add_field(
                    name="Definition",
                    value=definition_value,
                    inline=False
                )
                embeds.append(embed)
                embed = Embed(
                    title=word.capitalize(),
                    description=f"Pronunciation: `{phonetics}`"
                ).set_footer(text="Coded by ThanhZ")
        return PaginatedView(timeout=300, embeds=embeds)

    @commands.hybrid_command(name='dictionary', aliases=['dict'], description="Find a word in the dictionary")
    @app_commands.allowed_installs(guilds=True, users=True)
    async def dict_command(self, ctx: FurinaCtx, word: str):
        """
        Find a word in the dictionary
        
        Parameters
        -----------
        word: `str`
            - The word, note that it only get the first word
        """
        view = await self.dictionary_call(word.split()[0])
        view.message = await ctx.reply(embed=view.embeds[0], view=view)

async def setup(bot: FurinaBot):
    await bot.add_cog(Utils(bot))