from __future__ import annotations


from pathlib import Path
import asyncio, discord, logging, subprocess, textwrap, threading, wavelink
from discord.ext import commands
from discord import app_commands, ui, Color, ButtonStyle, Embed, Interaction, Message
from typing import TYPE_CHECKING, List, Union, cast
from wavelink import (Player, Playable, Playlist, TrackSource, TrackStartEventPayload, QueueMode,
                      TrackEndEventPayload, TrackExceptionEventPayload, AutoPlayMode, Node, Pool)
from youtube_search import YoutubeSearch


from bot import FurinaCtx
from _classes.views import PaginatedView
from settings import *

if TYPE_CHECKING:
    from bot import FurinaBot


class FooterEmbed(Embed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_footer(text="Coded by ThanhZ")


class Embeds:
    @staticmethod
    def nowplaying_embed(player: Player) -> Embed:
        """Embed phản hồi cho lệnh nowplaying"""
        current = player.current
        embed = FooterEmbed(title=f"Now Playing", description=f"### [{current}]({current.uri})\n", color=Color.blue())
        embed.set_author(icon_url=PLAYING_GIF, name=current.author)
        embed.set_image(url=current.artwork)
        played = int((player.position / current.length) * 20)
        embed.description += ('▰'*played + '▱'*(20-played))
        embed.description += f"\n`{format_len(player.position)} / {format_len(current.length)}`"
        return embed

    @staticmethod
    def error_embed(error: str) -> Embed:
        return FooterEmbed(title="Error", description=error)



class TrackUtils:
    """Some utilities for `wavelink.Playable`"""
    def __init__(self, track: Playable) -> None:
        self.__track = track
    
    @property
    def formatted_len(self) -> str:
        """Convert track len from `ms` to `mm:ss` format"""
        minutes, seconds = divmod(self.__track.length // 1000, 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def shortened_name(self) -> str:
        """Shorten the track name to 50 characters long"""
        return textwrap.shorten(self.__track.title, width=50, break_long_words=False, placeholder="...")
    

class PlayerUtils:
    @staticmethod
    async def __search_for_tracks(*, query: str, source: TrackSource = None) -> wavelink.Search:
        if "https://" not in query:
            ytsearch = YoutubeSearch(query, 1).to_dict()[0]
            query = f"https://youtu.be/{ytsearch['id']}"
            return await Playable.search(query)
        else:
            return await Playable.search(query, source=source)

    async def play(self, ctx: Union[FurinaCtx, Interaction], query: str, source: TrackSource = None) -> None:
        self.__ctx = ctx
        await self.__ctx.tick()
        await self.__ctx.defer()

        self.__searched = await self.__search_for_tracks(query=query, source=source)
        if not self.__searched:
            embed = self.__ctx.embed
            embed.title = "Cannot find any tracks with the given query"
            embed.color = Color.red()
            await self.__ctx.reply(embed=embed)
        
        await self.__add_to_queue()

    async def __add_to_queue(self) -> None:
        embed = self.__ctx.embed
        embed.color = Color.blue()
        embed.set_author(name="Loading...")
        if isinstance(self.__ctx, Interaction):
            interaction = self.__ctx
            msg = await interaction.edit_original_response(embed=embed, view=None)
        else:
            msg = await self.__ctx.reply(embed=embed, view=None)
        self.__player = await self.ensure_voice_connection()

        # If the bot is in a StageChannel, request to speak
        if isinstance(self.__player.channel, discord.StageChannel):
            await self.__player.channel.guild.me.edit(suppress=False)
        
        if isinstance(self.__searched, Playlist):
            embeds = await self.__add_playlist()
            view = PaginatedView(timeout=180, embeds=embeds)
            embed = embeds[0]
        else:
            view = None
            embed = await self.__add_song()
        await msg.edit(embed=embed, view=view)

    async def __add_playlist(self) -> List[Embed]:
        self.__searched = cast(Playlist, self.__searched)
        track_added: int = 0
        track_skipped: int = 0
        embed = self.__ctx.embed
        embed.description = ""
        embeds = []
        for track in self.__searched.tracks:
            if not track.is_stream:
                embed.description += f"- Added `{track}` to the queue\n"
                await self.__player.queue.put_wait(track)
                track_added += 1
            else:
                embed.description += f"- Skipped `{track}`\n"
                track_skipped += 1

            if (track_added + track_skipped) % 10 == 0: # Pagination
                embeds.append(embed)
                embed = self.__ctx.embed
                embed.description =  ""

        if embed.description != "":
            embeds.append(embed)
                
        for embed in embeds:
            embed.title = f"Added {track_added}, skipped {track_skipped} out of {len(self.__searched.tracks)} tracks"
        if not self.__player.playing:
            await self.__player.play(self.__player.queue.get(), populate=True)
        return embeds

    async def __add_song(self) -> Embed:
        self.__searched = cast(List[Playable], self.__searched)
        track = self.__searched[0]
        embed = self.__ctx.embed
        if track.is_stream:
            embed.title = "Cannot play a livestream"
            embed.color = Color.red()
            return embed
        await self.__player.queue.put_wait(track)

        if not self.__player.playing:
            await self.__player.play(self.__player.queue.get(), populate=True)
        embed.title = "Added to queue"
        embed.color = Color.green()
        embed.description = f"### Track: [{track}]({track.uri}) ({TrackUtils(track).formatted_len})"
        embed.set_author(name=track.author)
        embed.set_image(url=track.artwork)
        if self.__player.queue.count > 0:
            embed.add_field(name="Number in queue", value=self.__player.queue.count)
        return embed

    async def ensure_voice_connection(self, ctx: FurinaCtx = None) -> Player:
        ctx = ctx or self.__ctx
        try:
            if ctx.guild.voice_client:
                return cast(Player, self.__ctx.guild.voice_client)
            channel = ctx.author.voice.channel if isinstance(ctx, FurinaCtx) else ctx.user.voice.channel
            return await channel.connect(cls=Player, self_deaf=True)
        except wavelink.exceptions.ChannelTimeoutException:
            await ctx.channel.send("Bot cannot connect to the channel...", delete_after=10.0)


class SelectTrackView(ui.View):
    def __init__(self, yt_tracks: list[Playable], sc_tracks: list[Playable]):
        super().__init__(timeout=180)
        self.message: Message | None = None
        self.add_item(SelectTrack(yt_tracks, placeholder="YouTube"))
        self.add_item(SelectTrack(sc_tracks, placeholder="SoundCloud"))

    async def on_timeout(self) -> None:
        self.stop()
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)


class SelectTrack(ui.Select):
    def __init__(self, tracks: list[Playable], *, placeholder: str) -> None:
        super().__init__(
            placeholder=placeholder,
            options=[]
        )
        self.tracks = tracks

        for i, track in enumerate(tracks):
            self.options.append(
                discord.SelectOption(
                    label=f"{shorten_name(track)} ({format_len(track.length)})",
                    value=str(i)
                )
            )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.view.message = None
        await add_to_queue(interaction, self.tracks[int(self.values[0])])


class LoopView(ui.View):
    def __init__(self, *, player: Player):
        super().__init__(timeout=60)
        self.player = player
        if self.player.queue.mode == QueueMode.normal:
            self.loop_off.style = ButtonStyle.green
        elif self.player.queue.mode == QueueMode.loop:
            self.loop_current.style = ButtonStyle.green
        else:
            self.loop_all.style = ButtonStyle.green

    @ui.button(emoji="\U0000274e", style=ButtonStyle.grey)
    async def loop_off(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = QueueMode.normal
        await self.mass_button_style_change(button)

    @ui.button(emoji="\U0001f502", style=ButtonStyle.grey)
    async def loop_current(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = QueueMode.loop_all
        await self.mass_button_style_change(button)

    @ui.button(emoji="\U0001f501", style=ButtonStyle.grey)
    async def loop_all(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = QueueMode.loop
        await self.mass_button_style_change(button)

    async def mass_button_style_change(self, button: ui.Button):
        for child in self.children:
            if child == button:
                child.style = ButtonStyle.green
            else:
                child.style = ButtonStyle.grey
        await self.message.edit(view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)


class Music(commands.Cog):
    """Music Related Commands"""
    def __init__(self, bot: FurinaBot):
        self.bot = bot
        self.webhook = discord.SyncWebhook.from_url(MUSIC_WEBHOOK)

    async def cog_load(self) -> None:
        version = await self.get_lavalink_jar()
        self.start_lavalink(version)
        await asyncio.sleep(10)
        await self.refresh_node_connection()

    async def get_lavalink_jar(self) -> str:
        async with self.bot.cs.get("https://api.github.com/repos/lavalink-devs/Lavalink/releases/latest") as response:
            release_info = await response.json()
        try:
            jar_info = next(
                (asset for asset in release_info["assets"] if asset["name"] == "Lavalink.jar"),
                None
            )
            version_info = release_info["tag_name"]
        except KeyError:
            return
        ll_path = Path(f"Lavalink-{version_info}.jar")
        if ll_path.exists():
            logging.info(f"Lavalink.jar is up-to-date (v{version_info}). Skipping download...")
        else:
            try:
                file = [file for file in os.listdir() if (file.startswith("Lavalink-") and file.endswith(".jar"))]
                os.remove(file[0])
            except IndexError:
                pass
            logging.info("Deleted outdated Lavalink.jar file. Downloading new version...")
            jar_url = jar_info["browser_download_url"]
            async with self.bot.cs.get(jar_url) as jar:
                with open(f"./Lavalink-{version_info}.jar", "wb") as f:
                    f.write(await jar.read())
                    logging.info(f"Successfully downloaded Lavalink.jar (v{version_info})")
        return version_info
            
    def start_lavalink(self, version: str):
        def run_lavalink():
            try:
                subprocess.run(["java", "-jar", f"Lavalink-{version}.jar"], cwd="./")
            except FileNotFoundError as e:
                logging.error(f"Java is not installed or not in PATH: {e}")
                print(f"Java is not installed or not in PATH: {e}")
                raise e
            except subprocess.CalledProcessError as e:
                logging.error(f"Error starting Lavalink: {e}")
                print(f"Error starting Lavalink: {e}")
                raise e
            except Exception as e:
                logging.error(f"An error occured when starting Lavalink: {e}")
                print(f"An error occured when starting Lavalink: {e}")
        try:
            thread = threading.Thread(target=run_lavalink, daemon=True)
            thread.start()
        except Exception as e:
            pass

    async def cog_check(self, ctx: FurinaCtx) -> bool:
        embed = ctx.embed
        embed.color = Color.red()
        embed.title = "Error"
        if not self._is_connected(ctx):
            embed.description = "You need to join a voice channel to use this"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_music_channel(ctx):
            embed.description = f"This command can only be used in <#{MUSIC_CHANNEL}>"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_same_channel(ctx):
            embed.description = (f"You and {ctx.me.mention} are not in the same voice channel.\n"
                                 f"{ctx.me.mention} is in {ctx.guild.me.voice.channel.mention}")
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        return True
        
    async def refresh_node_connection(self) -> None:
        try:
            Pool.get_node()
        except wavelink.InvalidNodeException:
            node = Node(uri=LAVA_URI, password=LAVA_PW, heartbeat=5.0, inactive_player_timeout=None)
            await Pool.close()
            try:
                await Pool.connect(client=self.bot, nodes=[node])
                print(f"Connected to \"{node.uri}\"")
            except wavelink.NodeException:
                node = Node(uri=BACKUP_LL, password=BACKUP_LL_PW, heartbeat=5.0, inactive_player_timeout=None)

    @staticmethod
    def _is_connected(ctx: FurinaCtx) -> bool:
        """Whether the author is connected or not"""
        return ctx.author.voice is not None

    @staticmethod
    def _is_in_music_channel(ctx: FurinaCtx) -> bool:
        """Whether the command is executed in music channel or not"""
        return ctx.message.channel.id == MUSIC_CHANNEL

    @staticmethod
    def _is_in_same_channel(ctx: FurinaCtx) -> bool:
        """Whether the bot is in the same voice channel with the author or not"""
        bot_connected = ctx.guild.me.voice
        # Bot not in voice channel, return True
        if not bot_connected:
            return True
        return bot_connected.channel.id == ctx.author.voice.channel.id

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload):
        """Xử lý khi bài hát kết thúc."""
        player: Player = payload.player
        if not player:
            return
        if player.autoplay == AutoPlayMode.enabled:
            return
        if hasattr(player, "queue") and not player.queue.is_empty:
            await player.play(player.queue.get())
        else:
            embed = self.bot.embed
            embed.title = "Queue is empty"
            self.webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload):
        """Sends an embed notify the track started playing"""
        track: Playable = payload.track
        embed = self.bot.embed
        embed.title = f"Playing: **{track}**"
        embed.url = track.uri
        embed.set_author(name=track.author, icon_url=PLAYING_GIF)
        embed.set_thumbnail(url=track.artwork)
        self.webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: TrackExceptionEventPayload):
        """Sends an embed notify an exception occured while playing"""
        embed = Embeds.error_embed(f"An error occured while playing {payload.track.title}\n"
                                   f"Detailed error:\n"
                                   f"```\n"
                                   f"{payload.exception}\n"
                                   f"```")
        logging.exception(f"An error occured while playing {payload.track}\n{payload.exception}")
        self.webhook.send(embed=embed)

    @staticmethod
    def _get_player(ctx: FurinaCtx) -> Player:
        """Get `wavelink.Player` from ctx"""
        return cast(Player, ctx.guild.voice_client)

    @commands.hybrid_group(name='play', aliases=['p'], description="Play music")
    async def play_command(self, ctx: FurinaCtx, *, query: str):
        """
        Play music from YouTube. Prefix only

        Parameters
        -----------
        query: str
            - Name or link to the music
        """
        await PlayerUtils().play(ctx, query)

    @play_command.command(name='youtube', aliases=['yt'], description="Phát một bài hát từ YouTube")
    async def play_yt_command(self, ctx: commands.Context, *, query: str):
        """
        Phát một bài hát từ YouTube

        Parameters
        -----------
        ctx: commands.Context
            Context
        query: str
            Tên bài hát hoặc link dẫn đến bài hát
        """
        await PlayerUtils().play(ctx, query)

    @play_command.command(name='youtubemusic', aliases=['ytm'], description="Phát một bài hát từ YouTube Music")
    async def play_ytm_command(self, ctx: commands.Context, *, query: str):
        """
        Phát một bài hát từ YouTube Music

        Parameters
        -----------
        ctx: commands.Context
            Context
        query: str
            Tên bài hát hoặc link dẫn đến bài hát
        """
        await PlayerUtils().play(ctx, query, TrackSource.YouTubeMusic)

    @play_command.command(name='soundcloud', aliases=['sc'], description="Phát một bài hát từ SoundCloud")
    async def play_sc_command(self, ctx: commands.Context, *, query: str):
        """
        Phát một bài hát từ SoundCloud

        Parameters
        -----------
        ctx: commands.Context
            Context
        query: str
            Tên bài hát hoặc link dẫn đến bài hát
        """
        await PlayerUtils.play(ctx, query, TrackSource.SoundCloud)

    @commands.hybrid_command(name='search', aliases=['s'], description="Tìm kiếm một bài hát.")
    async def search_command(self, ctx: commands.Context, *, query: str):
        """
        Tìm kiếm một bài hát.

        Parameters
        -----------
        ctx
            commands.Context
        query
            Tên bài hát cần tìm
        """
        await ctx.defer()
        msg = await ctx.reply(embed=FooterEmbed(description=f"**Đang tìm kiếm:** `{query}`"))
        tracks_yt = []
        for yttrack in YoutubeSearch(query, 5).to_dict():
            for key, value in yttrack.items():
                if key == "id":
                    results = await Playable.search(f"https://youtu.be/{value}")
                    tracks_yt.append(results[0])

        tracks_sc: wavelink.Search = await Playable.search(query, source=TrackSource.SoundCloud)


        view = SelectTrackView(tracks_yt[:5], tracks_sc[:5])
        tracks = tracks_yt[:5] + tracks_sc[:5]

        if len(tracks) == 0:
            return msg.edit(embed=Embeds.error_embed(f"Không tìm thấy kết quả nào cho `query`"))
        else:
            await msg.edit(embed=FooterEmbed(title=f"Kết quả tìm kiếm cho `{query}`"), view=view)

    @commands.hybrid_command(name='pause', description="Tạm dừng việc phát nhạc")
    async def pause_command(self, ctx: commands.Context) -> None:
        """Tạm dừng việc phát nhạc."""
        player: Player = self._get_player(ctx)
        await player.pause(True)
        embed = FooterEmbed(title="Đã tạm dừng chơi nhạc", description="Dùng `!resume` hoặc `/resume` để tiếp tục")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='resume', description="Tiếp tục việc phát nhạc")
    async def resume_command(self, ctx: commands.Context) -> None:
        """Tiếp tục việc phát nhạc."""
        player: Player = self._get_player(ctx)
        await player.pause(False)
        embed = FooterEmbed(title="Đã tiếp tục chơi nhạc", description="Dùng `!pause` hoặc `/pause` để tạm dừng")
        await ctx.reply(embed=embed)

    @commands.hybrid_group(name='autoplay', aliases=['auto'], description="Bật hoặc tắt tự động phát.")
    async def autoplay_switch(self, ctx: commands.Context):
        """Bật hoặc tắt tự động phát."""
        player: Player = self._get_player(ctx)
        if player.autoplay == AutoPlayMode.disabled:
            switch_to_mode: str = "bật"
            player.autoplay = AutoPlayMode.enabled
        else:
            switch_to_mode: str = "tắt"
            player.autoplay = AutoPlayMode.disabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã {switch_to_mode} chế độ tự động phát"))

    @autoplay_switch.command(name='on', description="Bật tính năng tự động phát")
    async def autoplay_on(self, ctx: commands.Context):
        """Bật tính năng tự động phát."""
        player: Player = self._get_player(ctx)
        player.autoplay = AutoPlayMode.enabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã bật chế độ tự động phát"))

    @autoplay_switch.command(name='off', description="Tắt tính năng tự động phát")
    async def autoplay_off(self, ctx: commands.Context):
        """Tắt tính năng tự động phát."""
        player: Player = self._get_player(ctx)
        player.autoplay = AutoPlayMode.disabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã tắt chế độ tự động phát"))

    @commands.hybrid_command(name='nowplaying', aliases=['np', 'now', 'current'], description="Đang phát bài gì thế?")
    async def nowplaying_command(self, ctx: commands.Context):
        """Xem bài hát đang phát."""
        player: Player = self._get_player(ctx)
        await ctx.reply(embed=Embeds.nowplaying_embed(player))

    @commands.hybrid_command(name='skip', description="Bỏ qua bài hát hiện tại.")
    async def skip_command(self, ctx: commands.Context):
        """Bỏ qua bài hát hiện tại."""
        player: Player = self._get_player(ctx)
        track = player.current
        if track:
            embed = Embed().set_author(name=f"Đã skip {track}", icon_url=SKIP_EMOJI)
            await player.seek(track.length)
        else:
            embed = Embeds.error_embed("Hiện đang không phát bất cứ thứ gì")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='stop', description="Dừng phát nhạc và xóa hàng chờ")
    async def stop_playing(self, ctx: commands.Context):
        """Tạm dừng phát nhạc và xóa hàng chờ."""
        player: Player = self._get_player(ctx)
        player.queue.clear()
        player.autoplay = AutoPlayMode.disabled
        await player.stop(force=True)
        embed = Embed().set_author(name=f"Đã dừng phát nhạc và xóa toàn bộ hàng chờ", icon_url=SKIP_EMOJI)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='queue', aliases=['q'], description="Xem chi tiết hàng chờ.")
    async def queue_command(self, ctx: commands.Context):
        """Show hàng chờ."""
        await self._show_queue(ctx)

    async def _show_queue(self, ctx: commands.Context):
        embeds: list[Embed] | Embed = self._queue_embeds(ctx)
        if isinstance(embeds, Embed):
            return await ctx.reply(embed=embeds)
        view = PaginatedView(timeout=60, embeds=embeds)
        view.message = await ctx.reply(embed=embeds[0], view=view)

    def _queue_embeds(self, ctx: commands.Context) -> list[Embed] | Embed:
        player: Player = self._get_player(ctx)
        if player.queue.is_empty:
            embed: Embed = FooterEmbed(title="Hàng chờ trống!")
            return embed
        queue_embeds: list[Embed] = []
        q: str = ""
        for i, track in enumerate(player.queue, 1):
            q += f"{i}. [**{track}**](<{track.uri}>) ({TrackUtils(track).formatted_len})\n"
            if i % 10 == 0:
                embed: Embed = self._create_queue_embed(player, q)
                queue_embeds.append(embed)
                q = ""
        if q:
            embed: Embed = self._create_queue_embed(player, q)
            queue_embeds.append(embed)
        return queue_embeds

    def _create_queue_embed(self, player: Player, q: str) -> Embed:
        embed = FooterEmbed(color=Color.blue(),
                                   title=f"Hàng chờ: {player.queue.count} bài hát",
                                   description=q)
        if player.playing:
            track = player.current
            embed.add_field(
                name="Đang phát",
                value=f"[**{track}**](<{track.uri}>) ({TrackUtils(track).formatted_len})"
                )
        return embed

    @app_commands.command(name='remove', description="Xóa một bài hát khỏi hàng chờ")
    async def remove_slashcommand(self, interaction: discord.Interaction, track_name: str):
        """
        Xóa một bài hát khỏi hàng chờ.

        Parameters
        -----------
        ctx
            commands.Context
        track_name
            Tên bài hát cần xóa
        """
        player: Player = self._get_player(interaction)
        player.queue.remove(track for track in player.queue if track.title == track_name)
        deleted: str = track_name

        await interaction.response.send_message(embed=Embed(title=f"Đã xóa {deleted} khỏi hàng chờ."))

    @remove_slashcommand.autocomplete("track_name")
    async def remove_slashcommand_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice]:
        player: Player = self._get_player(interaction)
        return [app_commands.Choice(name=track.title, value=track.title) for track in player.queue if current.lower() in track.title.lower()][:25]
    
    @commands.command(name='remove', aliases=['rm', 'delete'], description="Xóa một bài hát khỏi hàng chờ")
    async def remove_prefixcommand(self, ctx: commands.Context):
        player: Player = self._get_player(ctx)
        if player.queue.is_empty:
            return
        track_index = player.queue.count - 1
        deleted: Playable = player.queue[track_index]
        del player.queue[track_index]
        await ctx.reply(embed=Embed(title=f"Đã xóa {deleted} khỏi hàng chờ."))  
        await self._show_queue(ctx)


    @commands.hybrid_command(name='loop', aliases=['repeat'], description="Chuyển đổi giữa các chế độ lặp")
    async def loop_command(self, ctx: commands.Context) -> None:
        player: Player = self._get_player(ctx)
        view = LoopView(player=player)
        view.message = await ctx.reply(view=view)

    @commands.hybrid_command(name='connect', aliases=['j', 'join'], description="Kết nối bot vào kênh thoại")
    async def connect_command(self, ctx: commands.Context):
        """Gọi bot vào kênh thoại"""
        player: Player = await PlayerUtils().ensure_voice_connection(ctx)
        embed = FooterEmbed(title="— Đã kết nối!", description=f"Đã vào kênh {player.channel.mention}.")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='disconnect', aliases=['dc', 'leave', 'l'], description="Ngắt kết nối bot khỏi kênh thoại")
    async def disconnect_command(self, ctx: commands.Context):
        if ctx.voice_client:
            embed = FooterEmbed(title="— Đã ngắt kết nối!", description=f"Đã rời kênh {ctx.voice_client.channel.mention}")
            await ctx.voice_client.disconnect(force=True)
        else:
            embed = Embeds.error_embed("Bot không nằm trong kênh thoại nào.")
        await ctx.reply(embed=embed)


async def setup(bot: FurinaBot):
    await bot.add_cog(Music(bot))
