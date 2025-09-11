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
from typing import TYPE_CHECKING, Any

from discord import (
    Activity,
    ActivityType,
    DMChannel,
    Guild,
    Interaction,
    Member,
    Message,
    app_commands,
    ui,
)
from discord.ext import commands

from core import FurinaCog, FurinaCtx, settings

if TYPE_CHECKING:
    from wavelink import Playable, Player, TrackEndEventPayload, TrackStartEventPayload

    from core import FurinaBot


class BotEvents(FurinaCog):
    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)
        self.pool = bot.pool
        self.bot = bot

    async def update_activity(self, state: str = "N̸o̸t̸h̸i̸n̸g̸") -> None:
        """Update the bot's activity to the playing track.

        Parameters
        ----------
        state: :class:`str`
            Track name
        """
        await self.bot.change_presence(
            activity=Activity(
                type=ActivityType.playing, name=settings.ACTIVITY_NAME, state=f"Playing: {state}"
            )
        )

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
        if ctx.guild is None and "jishaku" not in ctx.command.qualified_name:
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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: Any, after: Any) -> None:
        # Change activity when bot leave voice channel
        if member == self.bot.user and not after.channel:
            await self.update_activity()

        # Leave if the bot is the last one in the channel
        if before.channel and not after.channel:  # noqa: SIM102
            if len(before.channel.members) == 1 and before.channel.members[0] == self.bot.user:
                await member.guild.voice_client.disconnect(force=True)
                channel = self.bot.get_partial_messageable(settings.MUSIC_CHANNEL)
                embed = self.bot.embed
                embed.title = "I am not afraid of ghost i swear :fearful:"
                embed.set_image(
                    url="https://media1.tenor.com/m/Cbwh3gVO4KAAAAAC/genshin-impact-furina.gif"
                )
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload) -> None:
        """Update activity if the queue is empty"""
        player: Player = payload.player
        if player.queue.is_empty:
            await self.update_activity()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload) -> None:
        """Update activity when a track starts playing"""
        track: Playable = payload.track
        await self.update_activity(track.title)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(BotEvents(bot))
