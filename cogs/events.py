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

import logging
import traceback
from typing import TYPE_CHECKING

from discord import DMChannel, Guild, Interaction, Message, app_commands, ui
from discord.ext import commands

from core import FurinaCog, FurinaCtx, settings
from core.views import Container, LayoutView

if TYPE_CHECKING:
    from core import FurinaBot


class BotEvents(FurinaCog):
    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)
        self.pool = bot.pool
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        """Add the guild to the database when the bot joins a new server"""
        await self.pool.execute("INSERT INTO guilds (id) VALUES (?)", guild.id)
        logging.info("Joined guild: %s (%s)", guild.name, guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        """Remove the guild from the database when the bot leaves a server"""
        await self.pool.execute("DELETE FROM guilds WHERE id = ?", guild.id)
        logging.info("Left guild: %s (%s)", guild.name, guild.id)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: FurinaCtx) -> None:
        """Save users to the database when they successfully use a command"""
        if ctx.guild is None or "jishaku" in ctx.command.qualified_name:
            return
        if len(self.bot.command_cache[ctx.guild.id]) == 10:
            self.bot.command_cache[ctx.guild.id].pop(0)
        self.bot.command_cache[ctx.guild.id].append(ctx.command.qualified_name)
        await self.pool.execute("INSERT OR REPLACE INTO users (id) VALUES (?)", ctx.author.id)
        await self.pool.execute(
            "INSERT INTO prefix_commands (guild_id, author_id, command) VALUES (?, ?, ?)",
            ctx.guild.id,
            ctx.author.id,
            ctx.command.qualified_name,
        )

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, interaction: Interaction, command: app_commands.Command | app_commands.ContextMenu
    ) -> None:
        """Save users to the database when they successfully use a command"""
        if interaction.guild is None:
            return
        if len(self.bot.app_command_cache[interaction.guild.id]) == 10:
            self.bot.app_command_cache[interaction.guild.id].pop(0)
        self.bot.app_command_cache[interaction.guild.id].append(command.qualified_name)
        await self.pool.execute("INSERT OR REPLACE INTO users (id) VALUES (?)", interaction.user.id)
        await self.pool.execute(
            "INSERT INTO app_commands (guild_id, author_id, command) VALUES (?, ?, ?)",
            interaction.guild.id,
            interaction.user.id,
            command.qualified_name,
        )

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot:
            return

        # Bot's DM will be logged anonymously
        if isinstance(message.channel, DMChannel):
            await message.forward(self.bot.get_user(self.bot.owner_id))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: FurinaCtx, error: commands.errors.CommandError) -> None:
        err: str = settings.CROSS
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            err += f" **Missing required argument:** `{error.param.name}`"
        else:
            err += f" **{error}**"
        view = ui.LayoutView().add_item(ui.Container(ui.TextDisplay(err)))
        await ctx.reply(view=view, ephemeral=True, delete_after=60)

        traceback.print_exception(error)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(BotEvents(bot))
