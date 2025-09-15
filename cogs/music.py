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

import typing
from typing import TYPE_CHECKING

import discord
import lavalink
from discord import Color, Embed, Interaction, app_commands, ui
from discord.ext import commands
from lavalink.errors import ClientError
from lavalink.events import TrackStartEvent
from lavalink.server import LoadType

from core import FurinaCog, FurinaCtx, settings
from core.utils import URL_REGEX
from core.views import Container, LayoutView, PaginatedView

if TYPE_CHECKING:
    from core import FurinaBot


class TrackNotFound(Exception): ...


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


def ms_to_mm_ss(length: int) -> str:
    """Converts milliseconds to "mm:ss" format

    Parameters
    ----------
    length : int
        Length in milliseconds

    Returns
    -------
    str
        Time in "mm:ss" format
    """
    mins, secs = divmod(length // 1000, 60)
    return f"{mins:02d}:{secs:02d}"


async def create_player_check(ctx: FurinaCtx) -> bool:
    """A check to see if we need to create a player"""
    if not ctx.guild:
        raise commands.CommandInvokeError("""You can't use this command in DM""")

    player: lavalink.DefaultPlayer = ctx.bot.lavalink.player_manager.create(ctx.guild.id)

    should_connect = ctx.command.name == "play"

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
        await ctx.author.voice.channel.connect(cls=VoiceProtocol, self_deaf=True)
    elif voice_client.channel.id != voice_channel.id:
        raise commands.CommandInvokeError("You need to be in my voicechannel.")

    return True


class Music(FurinaCog):
    """Music Related Commands"""

    def __init__(self, bot: FurinaBot) -> None:
        super().__init__(bot)

        self.lavalink: lavalink.Client = bot.lavalink
        self.lavalink.add_event_hooks(self)

    async def cog_unload(self) -> None:
        self.lavalink.remove_event_hooks(hooks=[self.on_track_start])
        return await super().cog_unload()

    async def cog_check(self, ctx: FurinaCtx) -> bool:
        if ctx.command.name in ("allowmusic", "disallowmusic"):
            return True
        channel_id: int = await ctx.bot.pool.fetchval(
            """SELECT channel_id FROM music_channel WHERE guild_id = ?""", ctx.guild.id
        )
        if ctx.channel.id == channel_id:
            return True
        raise commands.CommandInvokeError("""Music commands are not allowed in this channel""")

    @property
    def embed(self) -> Embed:
        return self.bot.embed

    def _get_player(self, ctx: FurinaCtx) -> lavalink.DefaultPlayer:
        return self.lavalink.player_manager.get(ctx.guild.id)

    @lavalink.listener(TrackStartEvent)
    async def on_track_start(self, event: TrackStartEvent) -> None:
        """Sends an embed notify the track started playing"""
        guild_id = event.player.guild_id
        guild = self.bot.get_guild(guild_id)

        if not guild:
            await self.lavalink.player_manager.destroy(guild_id)
            return
        channel = guild.get_channel(event.player.fetch("channel"))

        track = event.track
        view = LayoutView(
            Container(
                ui.Section(
                    f"### {settings.PLAYING_EMOJI} [**{track.title}**](<{track.uri}>)\n"
                    f"> **By:** {track.author}\n"
                    f"> **Duration:** `{ms_to_mm_ss(track.duration)}`\n"
                    f"> **Requester:** <@{track.extra['requester']}>",
                    accessory=ui.Thumbnail(track.artwork_url),
                )
            )
        )
        await channel.send(view=view, silent=True)

    async def play_music(
        self, ctx: FurinaCtx, *, search_prefix: str | None = None, query: str
    ) -> None:
        """Searches and plays a track with given query

        Defaults to `ytsearch` prefix if no prefix is specified.

        Parameters
        ----------
        query : str
            The query
        search_prefix : str | None, optional
            The prefix to search with lavalink, by default None

        Raises
        ------
        TrackNotFound
            If lavalink node cannot find any tracks with given query
        """
        player = self._get_player(ctx)
        query = query.strip("<>")

        if not URL_REGEX.match(query):
            query = f"{search_prefix}:{query}"

        results = await player.node.get_tracks(query)

        # Valid load_types are:
        #   TRACK    - direct URL to a track
        #   PLAYLIST - direct URL to playlist
        #   SEARCH   - query prefixed with either "ytsearch:" or "scsearch:".
        #                  This could possibly be expanded with plugins.
        #   EMPTY    - no results for the query (result.tracks will be empty)
        #   ERROR    - the track encountered an exception during loading
        if results.load_type == LoadType.EMPTY:
            raise TrackNotFound("I couldn't find any tracks for that query.")
        container = Container()
        if results.load_type == LoadType.PLAYLIST:
            tracks = results.tracks

            for track in tracks:
                track.extra["requester"] = ctx.author.id
                player.add(track=track)

            container.add_item(
                ui.TextDisplay(
                    f"### Playlist Enqueued!\n{results.playlist_info.name} - {len(tracks)} tracks"
                )
            )
        else:
            track = results.tracks[0]
            container.add_item(
                ui.TextDisplay(f"### Track Enqueued\n[{track.title}](<{track.uri}>)")
            )
            track.extra["requester"] = ctx.author.id
            player.add(track=track)

        await ctx.reply(view=LayoutView(container))

        if not player.is_playing:
            await player.play()

    @commands.command(name="allowmusic")
    @commands.has_guild_permissions(manage_guild=True)
    async def allow_music_command(
        self, ctx: FurinaCtx, channel: discord.TextChannel | None = None
    ) -> None:
        """Allows music commands in a channel

        Adds the channel into the music commands whitelist.
        Defaults to the current channel if not specified.
        Use `disallowmusic` to disallow the channel frm using music commands.
        Can only be used by member with `Manage Server` permission.

        Parameters
        ----------
        channel: TextChannel, optional
            The channel you allow to use music commands
        """
        channel = channel or ctx.channel
        await ctx.bot.pool.execute(
            """
            INSERT OR REPLACE INTO music_channel (guild_id, channel_id)
            VALUES (?, ?)
            """,
            ctx.guild.id,
            channel.id,
        )
        await ctx.reply(
            view=LayoutView(
                Container(
                    ui.TextDisplay(
                        f"### {settings.CHECKMARK} Added {channel.mention} to music channel list"
                    )
                )
            )
        )

    @commands.command(name="disallowmusic")
    @commands.has_guild_permissions(manage_guild=True)
    async def disallow_music_command(
        self, ctx: FurinaCtx, channel: discord.TextChannel | None = None
    ) -> None:
        """Disallows music commands from a channel

        Removes the channel from the music commands whitelist.
        Defaults to the current channel if not specified.
        Use `allowmusic` to whitelist the channel again.
        Can only be used by member with `Manage Server` permission.

        Parameters
        ----------
        channel: TextChannel, optional
            The channel you want to remove from the music channel list
        """
        channel = channel or ctx.channel
        await ctx.bot.pool.execute(
            """
            DELETE FROM music_channel WHERE guild_id = ? and channel_id = ?
            """,
            ctx.guild.id,
            channel.id,
        )
        await ctx.reply(
            view=LayoutView(
                Container(
                    ui.TextDisplay(
                        f"### {settings.CHECKMARK} "
                        f"Removed {channel.mention} from music channel list"
                    )
                )
            )
        )

    @commands.hybrid_group(name="play", aliases=["p"], fallback="youtube")
    @commands.check(create_player_check)
    async def play_group(self, ctx: FurinaCtx, *, query: str) -> None:
        """Searches and plays a track from a given query

        Use `play <track name>` or `play <track url>` to search and play the track.
        Use `play <playlist url>` to search and play the playlist.

        Parameters
        ----------
        query : str
            The query
        """
        await self.play_music(ctx, search_prefix="ytsearch", query=query)

    @play_group.command(name="soundcloud", aliases=["sc"])
    async def play_soundcloud(self, ctx: FurinaCtx, *, query: str) -> None:
        """Searches and plays a track from a given query

        Use `play soundcloud <track name>`
        or `play soundcloud <track url>` to search and play the track.

        Parameters
        ----------
        query : str
            The query
        """
        await self.play_music(ctx, search_prefix="scsearch", query=query)

    @commands.hybrid_command(name="pause")
    async def pause_command(self, ctx: FurinaCtx) -> None:
        """Pauses the player"""
        player = self._get_player(ctx)
        await player.set_pause(True)
        container = Container(
            ui.TextDisplay(
                "### Paused the player\n"
                f"-# Use `{ctx.prefix}resume` or `/resume` to continue playing"
            )
        )
        await ctx.reply(view=LayoutView(container))

    @commands.hybrid_command(name="resume", aliases=["unpause"])
    async def resume_command(self, ctx: FurinaCtx) -> None:
        """Unpauses the player"""
        player = self._get_player(ctx)
        await player.set_pause(False)
        container = Container(
            ui.TextDisplay(
                f"### Resumed the player\n-# Use `{ctx.prefix}pause` or `/pause` to pause"
            )
        )
        await ctx.reply(view=LayoutView(container))

    @commands.hybrid_command(name="nowplaying", aliases=["np", "now", "current"])
    async def nowplaying_command(self, ctx: FurinaCtx) -> None:
        """Gets the on going track

        Get the title, url, thumbnail and the current position of the track.
        """
        player = self._get_player(ctx)
        current = player.current
        played = int((player.position / current.duration) * 20)
        container = Container(
            ui.TextDisplay(
                f"## {settings.PLAYING_EMOJI} Now playing\n"
                f"### [{current.title}]({current.uri})\n"
                f"> **By:** {current.author}\n"
                f"> **Requester:** <@{current.extra['requester']}>\n"
            ),
            ui.MediaGallery(discord.MediaGalleryItem(current.artwork_url)),
            ui.Separator(),
            ui.TextDisplay(
                ("▰" * played + "▱" * (20 - played) + "\n") + f"`{ms_to_mm_ss(player.position)} / "
                f"{ms_to_mm_ss(current.duration)}`"
            ),
        )
        await ctx.reply(view=LayoutView(container), allowed_mentions=None)

    @commands.hybrid_command(name="skip")
    async def skip_command(self, ctx: FurinaCtx) -> None:
        """Skips the current track"""
        player = self._get_player(ctx)
        track = player.current
        if track:
            embed = Embed().set_author(name=f"Skipped {track.title}", icon_url=settings.SKIP_EMOJI)
            await player.skip()
        else:
            embed = self.embed
            embed.title = "Error"
            embed.description = "Bot is not playing anything"
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="stop")
    async def stop_playing(self, ctx: FurinaCtx) -> None:
        """Stops playing and clears the queue"""
        player = self._get_player(ctx)
        player.queue.clear()
        await player.stop(force=True)
        embed = Embed().set_author(
            name="Stopped playing and cleared the queue", icon_url=settings.SKIP_EMOJI
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="queue", aliases=["q"])
    async def queue_command(self, ctx: FurinaCtx) -> None:
        """Shows the queue"""
        await self._show_queue(ctx)

    async def _show_queue(self, ctx: FurinaCtx) -> None:
        embeds: list[Embed] | Embed = self._queue_embeds(ctx)
        if isinstance(embeds, Embed):
            await ctx.reply(embed=embeds)
            return
        view = PaginatedView(timeout=60, embeds=embeds)
        view.message = await ctx.reply(embed=embeds[0], view=view)

    def _queue_embeds(self, ctx: FurinaCtx) -> list[Embed] | Embed:
        player = self._get_player(ctx)
        if len(player.queue) == 0:
            embed = self.embed
            embed.title = "Queue is empty"
            return embed
        queue_embeds: list[Embed] = []
        q: str = ""
        for i, track in enumerate(player.queue, 1):
            q += f"{i}. [**{track.title}**](<{track.uri}>) ({ms_to_mm_ss(track.duration)})\n"
            if i % 10 == 0:
                embed = self._create_queue_embed(player, q)
                queue_embeds.append(embed)
                q = ""
        if q:
            embed = self._create_queue_embed(player, q)
            queue_embeds.append(embed)
        return queue_embeds

    def _create_queue_embed(self, player: lavalink.DefaultPlayer, q: str) -> Embed:
        embed = self.embed
        embed.color = Color.blue()
        embed.title = f"Queued: {len(player.queue)} tracks"
        embed.description = q

        if player.is_playing:
            track = player.current
            embed.add_field(
                name="Playing",
                value=f"[**{track.title}**](<{track.uri}>) ({ms_to_mm_ss(track.duration)})",
            )
        return embed

    @app_commands.command(name="remove")
    async def remove_slashcommand(self, interaction: Interaction, track_name: str) -> None:
        """Removes a track from the queue

        Parameters
        -----------
        track_name
            Name of the track to remove
        """
        player = self._get_player(interaction)
        player.queue.remove(track for track in player.queue if track.title == track_name)
        deleted: str = track_name

        await interaction.response.send_message(
            embed=Embed(title=f"Removed {deleted} from the queue")
        )

    @remove_slashcommand.autocomplete("track_name")
    async def remove_slashcommand_autocomplete(
        self, interaction: Interaction, current: str
    ) -> list[app_commands.Choice]:
        player = self._get_player(interaction)
        return [
            app_commands.Choice(name=track.title, value=track.title)
            for track in player.queue
            if current.lower() in track.title.lower()
        ][:25]

    @commands.command(name="remove", aliases=["rm", "delete"])
    async def remove_prefixcommand(self, ctx: FurinaCtx) -> None:
        """Removes the last added track from the queue

        Only remove the last one from the queue.
        If you want to remove a specific one, use `/remove` instead.
        """
        player = self._get_player(ctx)
        if len(player.queue) == 0:
            return
        track_index = len(player.queue) - 1
        deleted = player.queue[track_index]
        del player.queue[track_index]
        await ctx.reply(embed=Embed(title=f"Removed {deleted} from the queue"))
        await self._show_queue(ctx)

    @commands.hybrid_command(name="disconnect", aliases=["dc", "leave", "l"])
    async def disconnect_command(self, ctx: FurinaCtx) -> None:
        """Disconnects the player"""
        if ctx.voice_client:
            await ctx.tick()
            await self._get_player(ctx).destroy()
            await ctx.voice_client.disconnect(force=True)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Music(bot))
