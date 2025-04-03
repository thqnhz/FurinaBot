from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

from discord import Activity, ActivityType, DMChannel, Message, Member
from discord.ext import commands
from wavelink import Player, Playable, TrackStartEventPayload, TrackEndEventPayload


from bot import FurinaCtx
from settings import MUSIC_CHANNEL, ACTIVITY_NAME


if TYPE_CHECKING:
    from bot import FurinaBot


class BotEvents(commands.Cog):
    def __init__(self, bot: FurinaBot) -> None:
        self.bot = bot

    async def update_activity(self, state: str = "N̸o̸t̸h̸i̸n̸g̸") -> None:
        """
        Update the bot's activity to the playing track.

        Parameters
        -----------
        bot: `commands.Bot`
            bot
        state: `str`
            Track name
        """
        await self.bot.change_presence(activity=Activity(type=ActivityType.playing, name=ACTIVITY_NAME, state=f"Playing: {state}"))

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        if message.author.bot:
            return

        # Processing DMs
        if isinstance(message.channel, DMChannel):
            owner = self.bot.get_user(self.bot.owner_id)
            embed = self.bot.embed
            embed.title = f"{message.author.mention} ({message.author.id}) sent a message"
            embed.description = ("`" + message.content + "`") if message.content else None
            if message.attachments:
                content = "\n".join(message.attachments)
            embed.timestamp = message.created_at

            await owner.send(content=content, embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: FurinaCtx, error: commands.errors.CommandError) -> None:
        embed = ctx.embed
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.description = f"Missing required argument: `{error.param.name}`"
        else:
            embed.description = f"{error}"
        await ctx.reply(embed=embed, ephemeral=True, delete_after=60)
        
        traceback.print_exception(error)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before, after) -> None:
        # Change activity when bot leave voice channel
        if member == self.bot.user and not after.channel:
            await self.update_activity()

        # Leave if the bot is the last one in the channel
        if before.channel and not after.channel:
            if len(before.channel.members) == 1 and before.channel.members[0] == self.bot.user:
                await member.guild.voice_client.disconnect(force=True)
                channel = self.bot.get_channel(MUSIC_CHANNEL)
                embed = self.bot.embed
                embed.title = "I am not afraid of ghost i swear :fearful:"
                embed.set_image(url="https://media1.tenor.com/m/Cbwh3gVO4KAAAAAC/genshin-impact-furina.gif")
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

