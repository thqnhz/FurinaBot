import discord, wavelink, textwrap
from discord.ext import commands
from discord import ButtonStyle, Color, Embed, Message, ui
from typing import TYPE_CHECKING, Optional, Literal, cast
from wavelink import (Player, Playable, Playlist, TrackSource, TrackStartEventPayload, QueueMode,
                      TrackEndEventPayload, TrackExceptionEventPayload, AutoPlayMode)
from youtube_search import YoutubeSearch


from settings import *

if TYPE_CHECKING:
    from bot import Furina


class FooterEmbed(Embed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_footer(text="Coded by ThanhZ")


class Embeds:
    @staticmethod
    def loading_embed() -> Embed:
        return FooterEmbed(color=Color.blue()).set_author(name="Đang tải...")
    
    @staticmethod
    def invalid_embed() -> Embed:
        return FooterEmbed(title="Lỗi",
                           description="Track dài hơn 2 tiếng hoặc là livestream. Vui lòng chọn track khác.",
                           color=Color.red())
    
    @staticmethod
    def added_embed(track: Playable, player: Player) -> Embed:
        """Embed phản hồi khi được thêm vào danh sách phát."""
        embed = FooterEmbed(title="Đã thêm vào hàng chờ", color=Color.green())
        embed.description = f"### Track: [{track}]({track.uri}) ({format_len(track.length)})"
        embed.set_author(name=track.author)
        embed.set_image(url=track.artwork)
        if player.queue.count > 0:
            embed.add_field(name="Thứ tự hàng chờ", value=player.queue.count)
        return embed

    @staticmethod
    def nowplaying_embed(player: Player) -> Embed:
        """Embed phản hồi cho lệnh nowplaying"""
        current = player.current
        embed = FooterEmbed(title=f"Đang phát", description=f"### [{current}]({current.uri})\n", color=Color.blue())
        embed.set_author(icon_url=PLAYING_GIF, name=current.author)
        embed.set_image(url=current.artwork)
        played = int((player.position / current.length) * 20)
        embed.description += ('▰'*played + '▱'*(20-played))
        embed.description += f"\n`{format_len(player.position)} / {format_len(current.length)}`"
        return embed

    @staticmethod
    def error_embed(error: str) -> Embed:
        return FooterEmbed(title="Lỗi", description=error)

    @staticmethod
    def player_embed(track: Playable) -> Embed:
        embed = FooterEmbed(title=f"Đang phát: **{track}**", url = track.uri)
        embed.set_author(name=track.author, icon_url=PLAYING_GIF)
        embed.set_thumbnail(url=track.artwork)
        return embed


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

    @ui.button(emoji="", style=ButtonStyle.grey)
    async def loop_off(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = QueueMode.normal
        await self.mass_button_style_change(button)

    @ui.button(emoji="", style=ButtonStyle.grey)
    async def loop_current(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = QueueMode.loop_all
        self.player.autoplay = AutoPlayMode.enabled
        await self.mass_button_style_change(button)

    @ui.button(emoji="", style=ButtonStyle.grey)
    async def loop_all(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = QueueMode.loop
        self.player.autoplay = AutoPlayMode.enabled
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


def format_len(length: int) -> str:
    """Chuyển đổi độ dài track sang dạng `phút:giây`"""
    minutes, seconds = divmod(length // 1000, 60)
    return f"{minutes:02d}:{seconds:02d}"

def shorten_name(track: Playable) -> str:
    """Rút gọn tên track xuống còn 50 ký tự."""
    return textwrap.shorten(track.title, width=50, break_long_words=False, placeholder="...")

def is_valid(track: Playable, player: Player = None) -> bool:
    """Kiểm tra xem track có hợp lệ để phát hay không."""
    if player and track in player.queue:
        return False
    return False if (track.is_stream or track.length // 3_600_000 > 2) else True

async def ensure_voice_connection(ctx: commands.Context | discord.Interaction) -> Player:
    try:
        if ctx.guild.voice_client:
            return cast(Player, ctx.guild.voice_client)
        elif isinstance(ctx, commands.Context):
            return await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)
        else:
            interaction = ctx
            return await interaction.user.voice.channel.connect(cls=Player, self_deaf=True)
    except wavelink.exceptions.ChannelTimeoutException:
        await ctx.channel.send("Bot không kết nối được với kênh thoại, đang thử kết nối lại với Lavalink...", delete_after=10.0)
        bot: "Furina" = ctx.bot if isinstance(ctx, commands.Context) else ctx.client
        await bot.refresh_node_connection()

async def add_to_queue(ctx: commands.Context | discord.Interaction, data: Playlist | Playable):
    msg = await loading_embed_reply(ctx)
    player = await ensure_voice_connection(ctx)
    while not player:
        player = await ensure_voice_connection(ctx)


    # Kiểm tra xem bot có đang ở trong StageChannel không để có thể request to speak
    if isinstance(player.channel, discord.StageChannel):
        await player.channel.guild.me.edit(suppress=False)

    async with ctx.channel.typing():
        if isinstance(data, Playlist):
            embed = await put_a_playlist(playlist=data, player=player)
        else:
            embed = await put_a_song(track=data, player=player)

        await msg.edit(embed=embed)

async def loading_embed_reply(ctx: commands.Context | discord.Interaction) -> Message:
    """Reply lệnh với `LoadingEmbed` và trả về `Message`"""
    if isinstance(ctx, discord.Interaction):
        interaction = ctx
        return await interaction.edit_original_response(embed=Embeds.loading_embed(), view=None)
    else:
        return await ctx.reply(embed=Embeds.loading_embed(), view=None)

async def put_a_song(*, track: Playable, player: Player) -> Embed:
    """Thêm một track vào hàng chờ."""
    if not is_valid(track):
        return Embeds.invalid_embed()
    await player.queue.put_wait(track)

    if not player.playing:
        await player.play(player.queue.get(), populate=True)
    return Embeds.added_embed(track=track, player=player)

async def put_a_playlist(*, playlist: Playlist, player: Player) -> Embed:
    """Thêm một playlist vào hàng chờ."""
    track_count: int = 0
    embed = FooterEmbed(description="")
    for track in playlist.tracks:
        if is_valid(track):
            embed.description += f"- Đã thêm `{track}` vào hàng chờ\n"
            await player.queue.put_wait(track)
            track_count += 1
        else:
            embed.description += f"- Đã bỏ qua `{track}`\n"
    embed.title = f"— Đã thêm {track_count} bài hát vào hàng chờ"
    embed.add_field(name="Để xem thứ tự các bài hát", value="Dùng `!queue` hoặc `/queue`")
    if not player.playing:
        await player.play(player.queue.get(), populate=True)
    return embed

async def play_music(ctx: commands.Context, track_name: str, source: TrackSource | str = None):
    if not ctx.interaction:
        await ctx.message.add_reaction(CHECKMARK)
    tracks = await search_for_tracks(track_name=track_name, source=source)
    if not tracks:
        return await ctx.reply(embed=Embeds.error_embed(f"Không tìm thấy kết quả nào cho `{track_name}`"))
    if isinstance(tracks, Playlist):
        return await add_to_queue(ctx, tracks)
    await add_to_queue(ctx, tracks[0])

async def search_for_tracks(track_name: str, source: TrackSource | str = None) -> wavelink.Search:
    if "https://" not in track_name:
        ytsearch = YoutubeSearch(track_name, 1).to_dict()[0]
        track_name = f"https://youtu.be/{ytsearch['id']}"
        return await Playable.search(track_name)
    else:
        return await Playable.search(track_name, source=source)


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


class QueueView(ui.View):
    def __init__(self, embeds: list[Embed]):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.page: int = 0
        self.message: Message | None = None
        if len(self.embeds) == 1:
            self.next_button.disabled = True

    @ui.button(emoji="\u25c0", disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        self.page -= 1
        if self.page == 0:
            button.disabled = True
        self.next_button.disabled = False
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @ui.button(emoji="\u25b6")
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        self.page += 1
        if self.page == len(self.embeds) - 1:
            button.disabled = True
        self.previous_button.disabled = False
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    async def on_timeout(self) -> None:
        self.stop()
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)


class Music(commands.Cog):
    """Lệnh liên quan đến việc chơi nhạc."""
    def __init__(self, bot: "Furina"):
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.refresh_node_connection()
        self.music_channel: discord.TextChannel = self.bot.get_channel(MUSIC_CHANNEL)
        if not self.music_channel:
            self.music_channel = await self.bot.fetch_channel(MUSIC_CHANNEL)

    async def cog_check(self, ctx: commands.Context) -> bool:
        embed = Embeds.error_embed("")
        if not self._is_connected(ctx):
            embed.description = "Bạn cần tham gia kênh thoại để sử dụng lệnh"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_music_channel(ctx):
            embed.description = f"Lệnh này chỉ có thể dùng được ở <#{MUSIC_CHANNEL}>"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_same_channel(ctx):
            embed.description = (f"Bạn và {ctx.me.mention} phải cùng ở một kênh thoại.\n"
                                 f"{ctx.me.mention} đang ở kênh {ctx.guild.me.voice.channel.mention}")
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        return True
        
    @staticmethod
    def _is_connected(ctx: commands.Context) -> bool:
        """Kiểm tra người dùng đã kết nối chưa."""
        return ctx.author.voice is not None

    @staticmethod
    def _is_in_music_channel(ctx: commands.Context) -> bool:
        """Kiểm tra tin nhẵn có đang ở kênh lệnh bật nhạc không."""
        return ctx.message.channel.id == MUSIC_CHANNEL

    @staticmethod
    def _is_in_same_channel(ctx: commands.Context) -> bool:
        """Kiểm tra xem bot và người dùng có ở cùng một kênh thoại hay không."""
        bot_connected = ctx.guild.me.voice
        # Nếu bot không trong kênh thoại nào thì trả về True
        if not bot_connected:
            return True
        return bot_connected.channel.id == ctx.author.voice.channel.id

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload):
        """Xử lý khi bài hát kết thúc."""
        player: Player = payload.player
        if player.autoplay == AutoPlayMode.enabled:
            return
        if hasattr(player, "queue") and not player.queue.is_empty:
            await player.play(player.queue.get(), populate=True, volume=50)
        else:
            embed = FooterEmbed(title="Không còn bài hát nào trong hàng chờ")
            await self.music_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload):
        """Xử lý khi bài hát bắt đầu."""
        track: Playable = payload.track
        embed = Embeds.player_embed(track=track)
        await self.music_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: TrackExceptionEventPayload):
        """Xử lý khi track bị lỗi khi đang phát."""
        embed: Embed = Embeds.error_embed(f"Có lỗi xuất hiện khi đang phát {payload.track.title}\n"
                                          f"Chi tiết lỗi:\n"
                                          f"```\n"
                                          f"{payload.exception}\n"
                                          f"```")
        await self.music_channel.send(embed=embed)

    @staticmethod
    def _get_player(ctx: commands.Context) -> Player:
        """Lấy `wavelink.Player` từ ctx."""
        return cast(Player, ctx.guild.voice_client)

    @commands.hybrid_group(name='play', aliases=['p'], description="Phát một bài hát")
    async def play_command(self, ctx: commands.Context, *, query: str):
        """
        Phát một bài hát từ YouTube. Prefix only

        Parameters
        -----------
        ctx: commands.Context
            Context
        query: str
            Tên bài hát hoặc link dẫn đến bài hát
        """
        await play_music(ctx, query)

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
        await play_music(ctx, query)

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
        await play_music(ctx, query, TrackSource.YouTubeMusic)

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
        await play_music(ctx, query, TrackSource.SoundCloud)

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
        view = QueueView(embeds)
        view.message = await ctx.reply(embed=embeds[0], view=view)

    def _queue_embeds(self, ctx: commands.Context) -> list[Embed] | Embed:
        player: Player = self._get_player(ctx)
        if player.queue.is_empty:
            embed: Embed = FooterEmbed(title="Hàng chờ trống!")
            return embed
        queue_embeds: list[Embed] = []
        q: str = ""
        for i, track in enumerate(player.queue, 1):
            q += f"{i}. [**{track}**](<{track.uri}>) ({format_len(track.length)})\n"
            if i % 5 == 0:
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
                value=f"[**{track}**](<{track.uri}>) ({format_len(track.length)})"
                )
        return embed

    @commands.hybrid_command(name='delete', aliases=['rm', 'remove'], description="Xóa một bài hát khỏi hàng chờ.")
    async def remove_track_command(self, ctx: commands.Context, number: Optional[int] = 0):
        """
        Xóa một bài hát khỏi hàng chờ.

        Parameters
        -----------
        ctx
            commands.Context
        number
            Số thứ tự bài hát trong hàng chờ, bỏ trống hoặc điền số 0 để xóa bài hát vừa đặt
        """
        player: Player = self._get_player(ctx)
        if number < 0 or number > player.queue.count:
            return
        else:
            track_index = player.queue.count - 1 if number == 0 else number - 1
            deleted = player.queue[track_index]
            del player.queue[track_index]
            await ctx.send(embed=Embed(title=f"Đã xóa {deleted} khỏi hàng chờ."))
            await self._show_queue(ctx)

    @commands.hybrid_command(name='loop', aliases=['repeat'], desciption="Chuyển đổi giữa các chế độ lặp.")
    async def loop_command(self, ctx: commands.Context) -> None:
        player = self._get_player(ctx)
        view = LoopView(player=player)
        view.message = await ctx.reply(view=view)

        

    @commands.hybrid_command(name='connect', aliases=['j', 'join'], description="Kết nối bot vào kênh thoại.")
    async def connect_command(self, ctx: commands.Context):
        """Gọi bot vào kênh thoại"""
        player = await ensure_voice_connection(ctx)
        embed = FooterEmbed(title="— Đã kết nối!", description=f"Đã vào kênh {player.channel.mention}.")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='disconnect', aliases=['dc', 'leave', 'l'], description="Ngắt kết nối bot khỏi kênh thoại.")
    async def disconnect_command(self, ctx: commands.Context):
        if ctx.voice_client:
            embed = FooterEmbed(title="— Đã ngắt kết nối!", description=f"Đã rời kênh {ctx.voice_client.channel.mention}")
            await ctx.voice_client.disconnect(force=True)
        else:
            embed = Embeds.error_embed("Bot không nằm trong kênh thoại nào.")
        await ctx.reply(embed=embed)


async def setup(bot: "Furina"):
    await bot.add_cog(Music(bot))
