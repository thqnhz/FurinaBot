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

import asyncio
import logging
import re
import textwrap
import typing
from typing import TYPE_CHECKING

import discord
from discord import ButtonStyle, Color, Embed, Interaction, Message, app_commands, ui
from discord.ext import commands
from lavalink.errors import ClientError
from lavalink.events import TrackEndEvent, TrackExceptionEvent, TrackStartEvent, TrackStuckEvent
from lavalink.server import LoadType

import lavalink
from core import FurinaCog, FurinaCtx, settings
from core.utils import URL_REGEX
from core.views import PaginatedView

if TYPE_CHECKING:
    from core import FurinaBot


class VoiceProtocol(discord.VoiceProtocol):
    def __init__(self, client: FurinaBot, channel: discord.abc.Connectable) -> None:
        super().__init__(client, channel)
        self.guild_id = self.channel.guild.id
        self._destroyed = False

        self.lavalink = client.lavalink

    async def _transform_voice_update_data(self, *, type_: str, data: typing.Any) -> None:
        """Transform voice update data and pass it into lavalink handler"""
        lavalink_data: dict[str, typing.Any] = {"t": type_, "d": data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_server_update(self, data: typing.Any) -> None:
        await self._transform_voice_update_data(type_="VOICE_SERVER_UPDATE", data=data)

    async def on_voice_state_update(self, data: typing.Any) -> None:
        channel_id = data["channel_id"]

        if not channel_id:
            await self._destroy()
            return

        self.channel = self.client.get_channel(int(channel_id))

        await self._transform_voice_update_data(type_="VOICE_STATE_UPDATE", data=data)

    async def connect(
        self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False
    ) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(
            channel=self.channel, self_mute=self_mute, self_deaf=self_deaf
        )

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player: lavalink.DefaultPlayer = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        await self._destroy()

    async def _destroy(self) -> None:
        self.cleanup()

        if self._destroyed:
            # Idempotency handling, if `disconnect()` is called, the changed voice state
            # could cause this to run a second time.
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass


def track_len_to_string(track: lavalink.AudioTrack) -> str:
    mins, secs = divmod(track.duration // 1000, 60)
    return f"{mins:02d}:{secs:02d}"


async def create_player_check(ctx: FurinaCtx) -> bool:
    """A check to see if we need to create a player"""
    if not ctx.guild:
        raise commands.CommandInvokeError("""You can't use this command in DM""")

    player: lavalink.DefaultPlayer = ctx.bot.lavalink.player_manager.create(ctx.guild.id)

    should_connect = ctx.command.name in ("play",)

    voice_client = ctx.voice_client

    if not ctx.author.voice or not ctx.author.voice.channel:
        # Check if we're in a voice channel. If we are, tell the user to join our voice channel.
        if voice_client is not None:
            raise commands.CommandInvokeError("""You need to join my voice channel first.""")

        # Otherwise, tell them to join any voice channel to begin playing music.
        raise commands.CommandInvokeError("""You are not in any voice channel.""")

    voice_channel = ctx.author.voice.channel

    if voice_client is None:
        if not should_connect:
            raise commands.CommandInvokeError("I'm not playing music.")

        permissions = voice_channel.permissions_for(ctx.me)

        if not permissions.connect or not permissions.speak:
            raise commands.CommandInvokeError("I need the `CONNECT` and `SPEAK` permissions.")

        if (
            voice_channel.user_limit > 0
            and len(voice_channel.members) >= voice_channel.user_limit
            and not ctx.me.guild_permissions.move_members
        ):
            raise commands.CommandInvokeError("Your voice channel is full!")

        player.store("channel", ctx.channel.id)
        await ctx.author.voice.channel.connect(cls=VoiceProtocol)
    elif voice_client.channel.id != voice_channel.id:
        raise commands.CommandInvokeError("You need to be in my voicechannel.")

    return True


class Music(FurinaCog):
    """Music Related Commands"""

    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)
        self.webhook = discord.SyncWebhook.from_url(settings.MUSIC_WEBHOOK)

        self.lavalink: lavalink.Client = bot.lavalink
        self.lavalink.add_event_hooks(self)

    @property
    def embed(self) -> Embed:
        return self.bot.embed

    async def cog_check(self, ctx: FurinaCtx) -> bool:
        embed = ctx.embed
        embed.color = Color.red()
        embed.title = "Error"
        if not self._is_connected(ctx):
            embed.description = "You need to join a voice channel to use this"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_music_channel(ctx):
            embed.description = f"This command can only be used in <#{settings.MUSIC_CHANNEL}>"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_same_channel(ctx):
            embed.description = (
                f"You and {ctx.me.mention} are not in the same voice channel.\n"
                f"{ctx.me.mention} is in {ctx.guild.me.voice.channel.mention}"
            )
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        return True

    @staticmethod
    def _is_connected(ctx: FurinaCtx) -> bool:
        """Whether the author is connected or not"""
        return ctx.author.voice is not None

    @staticmethod
    def _is_in_music_channel(ctx: FurinaCtx) -> bool:
        """Whether the command is executed in music channel or not"""
        return ctx.message.channel.id == settings.MUSIC_CHANNEL

    @staticmethod
    def _is_in_same_channel(ctx: FurinaCtx) -> bool:
        """Whether the bot is in the same voice channel with the author or not"""
        bot_connected = ctx.guild.me.voice
        # Bot not in voice channel, return True
        if not bot_connected:
            return True
        return bot_connected.channel.id == ctx.author.voice.channel.id

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent) -> None:
        """Sends an embed notify the track started playing"""
        guild_id = event.player.guild_id
        guild = self.bot.get_guild(guild_id)

        if not guild:
            await self.lavalink.player_manager.destroy(guild_id)
            return

        track: lavalink.AudioTrack = event.track
        embed = self.embed
        embed.title = f"Playing: **{track.title}**"
        embed.url = track.uri
        embed.set_author(name=track.author, icon_url=settings.PLAYING_GIF)
        embed.set_thumbnail(url=track.artwork_url)
        self.webhook.send(embed=embed)

    @commands.command(aliases=["p1"])
    @commands.check(create_player_check)
    async def play1(self, ctx: FurinaCtx, *, query: str) -> None:
        """Searches and plays a song from a given query."""
        # Get the player for this guild from cache.
        player: lavalink.DefaultPlayer = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip("<>")

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not URL_REGEX.match(query):
            query = f"ytsearch:{query}"

        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        embed = discord.Embed(color=discord.Color.blurple())

        # Valid load_types are:
        #   TRACK    - direct URL to a track
        #   PLAYLIST - direct URL to playlist
        #   SEARCH   - query prefixed with either "ytsearch:" or "scsearch:".
        #                  This could possibly be expanded with plugins.
        #   EMPTY    - no results for the query (result.tracks will be empty)
        #   ERROR    - the track encountered an exception during loading
        if results.load_type == LoadType.EMPTY:
            await ctx.send("I couldn'\t find any tracks for that query.")
            return
        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks

            # Add all of the tracks from the playlist to the queue.
            for track in tracks:
                # requester isn't necessary but it helps keep track of who queued what.
                # You can store additional metadata by passing it as a kwarg (i.e. key=value)
                # Requester can be set with `track.requester = ctx.author.id`.
                # Any other extra attributes must be set via track.extra.
                track.extra["requester"] = ctx.author.id
                player.add(track=track)

            embed.title = "Playlist Enqueued!"
            embed.description = f"{results.playlist_info.name} - {len(tracks)} tracks"
        else:
            track = results.tracks[0]
            embed.title = "Track Enqueued"
            embed.description = f"[{track.title}]({track.uri})"

            # requester isn't necessary but it helps keep track of who queued what.
            # You can store additional metadata by passing it as a kwarg (i.e. key=value)
            # Requester can be set with `track.requester = ctx.author.id`.
            # Any other extra attributes must be set via track.extra.
            track.extra["requester"] = ctx.author.id

            player.add(track=track)

        await ctx.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()

    @commands.hybrid_command(name="pause", description="Tạm dừng việc phát nhạc")
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def pause_command(self, ctx: FurinaCtx) -> None:
        """Tạm dừng việc phát nhạc."""
        player: VoiceProtocol = self._get_player(ctx)
        await player.pause(True)  # noqa: FBT003
        embed = self.embed
        embed.title = "Paused the player"
        embed.description = f"Use `{ctx.prefix}resume` or `/resume` to continue playing"
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="resume", description="Tiếp tục việc phát nhạc")
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def resume_command(self, ctx: FurinaCtx) -> None:
        """Tiếp tục việc phát nhạc."""
        player: VoiceProtocol = self._get_player(ctx)
        await player.pause(False)  # noqa: FBT003
        embed = self.embed
        embed.title = "Resumed the player"
        embed.description = f"Use `{ctx.prefix}pause` or `/pause` to pause"
        await ctx.reply(embed=embed)

    @commands.hybrid_command(
        name="nowplaying", aliases=["np", "now", "current"], description="Đang phát bài gì thế?"
    )
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def nowplaying_command(self, ctx: FurinaCtx) -> None:
        """Xem bài hát đang phát."""
        player: VoiceProtocol = self._get_player(ctx)
        current = player.current
        embed = ctx.embed
        embed.title = "Now Playing"
        embed.description = f"### [{current}]({current.uri})\n"
        embed.color = Color.blue()
        embed.set_author(icon_url=settings.PLAYING_GIF, name=current.author)
        embed.set_image(url=current.artwork)
        played = int((player.position / current.length) * 20)
        embed.description += "▰" * played + "▱" * (20 - played)
        # embed.description += (
        #     f"\n`{TrackUtils.format_len(player.position)} / {TrackUtils(current).formatted_len}`"
        # )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="skip", description="Bỏ qua bài hát hiện tại.")
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def skip_command(self, ctx: FurinaCtx) -> None:
        """Bỏ qua bài hát hiện tại."""
        player: VoiceProtocol = self._get_player(ctx)
        track = player.current
        if track:
            embed = Embed().set_author(name=f"Đã skip {track}", icon_url=settings.SKIP_EMOJI)
            await player.seek(track.length)
        else:
            embed = self.embed
            embed.title = "Error"
            embed.description = "Bot is not playing anything"
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="stop", description="Dừng phát nhạc và xóa hàng chờ")
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def stop_playing(self, ctx: FurinaCtx) -> None:
        """Tạm dừng phát nhạc và xóa hàng chờ."""
        player: VoiceProtocol = self._get_player(ctx)
        player.queue.clear()
        # player.autoplay = AutoPlayMode.disabled
        await player.stop(force=True)
        embed = Embed().set_author(
            name="Đã dừng phát nhạc và xóa toàn bộ hàng chờ", icon_url=settings.SKIP_EMOJI
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="queue", aliases=["q"], description="Xem chi tiết hàng chờ.")
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def queue_command(self, ctx: FurinaCtx) -> None:
        """Show hàng chờ."""
        await self._show_queue(ctx)

    async def _show_queue(self, ctx: FurinaCtx) -> None:
        embeds: list[Embed] | Embed = self._queue_embeds(ctx)
        if isinstance(embeds, Embed):
            await ctx.reply(embed=embeds)
            return
        view = PaginatedView(timeout=60, embeds=embeds)
        view.message = await ctx.reply(embed=embeds[0], view=view)

    # def _queue_embeds(self, ctx: FurinaCtx) -> list[Embed] | Embed:
    #     player: VoiceProtocol = self._get_player(ctx)
    #     if player.queue.is_empty:
    #         embed = self.embed
    #         embed.title = "Queue is empty"
    #         return embed
    #     queue_embeds: list[Embed] = []
    #     q: str = ""
    #     for i, track in enumerate(player.queue, 1):
    #         q += f"{i}. [**{track}**](<{track.uri}>) ({TrackUtils(track).formatted_len})\n"
    #         if i % 10 == 0:
    #             embed = self._create_queue_embed(player, q)
    #             queue_embeds.append(embed)
    #             q = ""
    #     if q:
    #         embed = self._create_queue_embed(player, q)
    #         queue_embeds.append(embed)
    #     return queue_embeds

    # def _create_queue_embed(self, player: VoiceProtocol, q: str) -> Embed:
    #     embed = self.embed
    #     embed.color = Color.blue()
    #     embed.title = f"Queued: {player.queue.count} tracks"
    #     embed.description = q

    #     if player.playing:
    #         track = player.current
    #         embed.add_field(
    #             name="Playing",
    #             value=f"[**{track}**](<{track.uri}>) ({TrackUtils(track).formatted_len})",
    #         )
    #     return embed

    @app_commands.command(name="remove", description="Xóa một bài hát khỏi hàng chờ")
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def remove_slashcommand(self, interaction: Interaction, track_name: str) -> None:
        """
        Xóa một bài hát khỏi hàng chờ.

        Parameters
        -----------
        track_name
            Tên bài hát cần xóa
        """
        player: VoiceProtocol = self._get_player(interaction)
        player.queue.remove(track for track in player.queue if track.title == track_name)
        deleted: str = track_name

        await interaction.response.send_message(
            embed=Embed(title=f"Đã xóa {deleted} khỏi hàng chờ.")
        )

    @remove_slashcommand.autocomplete("track_name")
    async def remove_slashcommand_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice]:
        player: VoiceProtocol = self._get_player(interaction)
        return [
            app_commands.Choice(name=track.title, value=track.title)
            for track in player.queue
            if current.lower() in track.title.lower()
        ][:25]

    # @commands.command(
    #     name="remove", aliases=["rm", "delete"], description="Xóa một bài hát khỏi hàng chờ"
    # )
    # async def remove_prefixcommand(self, ctx: FurinaCtx) -> None:
    #     player: VoiceProtocol = self._get_player(ctx)
    #     if player.queue.is_empty:
    #         return
    #     track_index = player.queue.count - 1
    #     deleted: Playable = player.queue[track_index]
    #     del player.queue[track_index]
    #     await ctx.reply(embed=Embed(title=f"Đã xóa {deleted} khỏi hàng chờ."))
    #     await self._show_queue(ctx)

    @commands.hybrid_command(
        name="disconnect",
        aliases=["dc", "leave", "l"],
        description="Ngắt kết nối bot khỏi kênh thoại",
    )
    @app_commands.guilds(settings.GUILD_SPECIFIC)
    async def disconnect_command(self, ctx: FurinaCtx) -> None:
        if ctx.voice_client:
            await ctx.tick()
            await ctx.voice_client.disconnect(force=True)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Music(bot))
