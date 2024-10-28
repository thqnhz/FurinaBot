import discord, wavelink, textwrap
from discord.ext import commands
from discord import Color, Embed, Activity, ActivityType, Message, ui
from typing import cast
from wavelink import (Player, Playable, Playlist, TrackSource, Node, Pool, TrackStartEventPayload,
                      TrackEndEventPayload, TrackExceptionEventPayload, AutoPlayMode)
from youtube_search import YoutubeSearch

# Custom subclasses
from _classes.embeds import *
from _classes.views import *
from _classes.buttons import *
from settings import *


async def update_activity(bot: commands.Bot, state: str = "N̸o̸t̸h̸i̸n̸g̸") -> None:
    """
    Cập nhật activity của bot theo bài hát đang phát.

    Parameters
    -----------
    bot: `commands.Bot`
        bot
    state: `str`
        Tên bài hát đang phát.
    """
    await bot.change_presence(
        activity=Activity(
            type=ActivityType.playing,
            name=ACTIVITY_NAME,
            state=f"Playing: {state}"
        )
    )

def length_convert(track: Playable) -> str:
    """
    Chuyển đổi từ milisecond sang phút:giây.

    Parameters
    -----------
    track: `wavelink.Playable`
        Track cần chuyển đổi
    
    Returns
    -----------
    `str`
        Thời gian đã được chuyển đổi từ milisecond thành `phút:giây`
    """
    return '{:02}:{:02}'.format(*divmod(track.length // 1000, 60))

def get_track_list(tracks: list[Playable] | None) -> str:
    """
    Chuyển đổi từ list[Playable] thành danh sách dạng string.

    Parameters
    -----------
    tracks: `list[Playable]` | None
        Danh sách Playable cần chuyển đổi.

    Returns
    ----------
    `str`
        Danh sách dạng string.
    """
    if not tracks:
        return "`không có kết quả nào`"
    else:
        track_list = ""
        for i, track in enumerate(tracks, 1):
            track_name = textwrap.shorten(track.title, width=50, break_long_words=False, placeholder="...")
            track_list += f"\n{i}. **[{track_name}]({track.uri})**\t({length_convert(track)})"
        return track_list

async def update_player_embed(embed: Embed,
                              msg: discord.Message,
                              channel,
                              view: discord.ui.View = None) -> None:
    if view is None:
        try:
            await msg.edit(embed=embed, view=view)
        except Exception as e:
            await channel.send(embed=embed)
            print(e)
    else:
        try:
            view.message = await msg.edit(embed=embed, view=view)
        except Exception as e:
            view.message = await channel.send(embed=embed, view=view)
            print(e)

def track_check(track: Playable) -> bool:
    """
    Kiểm tra xem track có phải là livestream hoặc có dài hơn 1 tiếng không.

    Parameters
    -----------
    track: `wavelink.Playable`
        Track cần kiểm tra

    Returns
    -----------
    bool
        - `True`: track có thể được thêm vào hàng chờ.
        - `False`: track sẽ không được thêm vào hàng chờ.
    """
    if hasattr(track, "is_stream"):
        if track.is_stream:
            return False
    return track.length // HOUR < 1
    
async def add_a_song(ctx: commands.Context, track: Playable, msg: Message) -> None:
        """
        Thêm một bài hát vào hàng chờ.

        Parameters
        -----------
        ctx: `commands.Context`
            Context
        track: `wavelink.Playable`
            Bài hát cần thêm vào hàng chờ
        msg: `discord.Message`
            Tin nhắn phản hồi ban đầu
        """
        if not track_check(track):
            return await msg.edit(
                embed=ErrorEmbed("""Bài hát bạn yêu cầu dài hơn 1 tiếng hoặc là bạn đang yêu cầu một livestream. Vui lòng chọn bài khác.""")
                )
        player = get_player(ctx)
        # track.extras = str(ctx.author.id) # TODO: Change bookers sang dùng track.extras
        await player.queue.put_wait(track)
        embed = FooterEmbed(title="— Đã thêm vào hàng chờ", color=Color.green())
        if track.artwork:
            embed.set_image(url=track.artwork)
        embed.set_author(name=track.author)
        embed.add_field(name="Tên bài hát", value=f"[**{track}**](<{track.uri}>)")
        embed.add_field(name="Độ dài", value=f"{length_convert(track)}")
        if player.playing:
            embed.add_field(name="Thứ tự hàng chờ", value=str(player.queue.count))
        else:
            await player.play(player.queue.get(), populate=True, volume=50)
        await msg.edit(embed=embed)

async def add_a_playlist(ctx: commands.Context, tracks: Playlist, msg: Message) -> None:
        """
        Thêm một danh sách phát vào hàng chờ.

        Parameters
        -----------
        ctx: `commands.Context`
            Context
        track: `wavelink.Playlist`
            Danh sách phát cần thêm vào hàng chờ
        msg: `discord.Message`
            Tin nhắn phản hồi ban đầu
        """
        track_count: int = 0
        embed = FooterEmbed(title=f"Đã thêm {track_count} bài hát vào hàng chờ", description="")
        player: Player = get_player(ctx)
        for track in tracks:
            if track_check(track):
                embed.description += f"- Đã thêm `{track}` vào hàng chờ\n"
                await player.queue.put_wait(track)
                track_count += 1
            else:
                embed.description += f"- Đã bỏ qua `{track}`\n"
            embed.title = f"— Đã thêm {track_count} bài hát vào hàng chờ"
            await msg.edit(embed=embed)
        embed.description = ""
        embed.add_field(
            name="Để xem thứ tự các bài hát",
            value="Dùng `!queue` hoặc `/queue`"
        )
        await msg.edit(embed=embed)
        if not player.playing:
            await player.play(player.queue.get(), populate=True, volume=50)

def get_player(ctx: commands.Context) -> Player:
        """
        Lấy wavelink.Player từ ctx.

        Parameters
        -----------
        ctx: `commands.Context`
            Context
        
        Returns
        -----------
        `wavelink.Player`
            Player lấy được từ việc cast `ctx.guild.voice_client` vào wavelink.Player
        """
        return cast(Player, ctx.guild.voice_client)

async def add_to_queue(ctx: commands.Context | discord.Interaction, data: Playlist | Playable):
    msg: Message
    if isinstance(ctx, discord.Interaction):
        interaction = ctx
        await interaction.edit_original_response(embed=LoadingEmbed())
        msg = await interaction.original_response()
    else:
        msg = await ctx.reply(embed=LoadingEmbed())
    player: Player = await ensure_voice_connection(ctx)

    # Kiểm tra xem bot có đang ở trong StageChannel không để có thể request to speak
    if isinstance(player.channel, discord.StageChannel):
        await player.channel.guild.me.edit(suppress=False)

    async with ctx.channel.typing():
        if isinstance(data, Playlist):
            await add_a_playlist(ctx, data, msg)
        else:
            await add_a_song(ctx, data, msg)

async def ensure_voice_connection(ctx: commands.Context | discord.Interaction) -> Player:
    player: Player
    if not ctx.guild.voice_client:
        if isinstance(ctx, discord.Interaction):
            interaction = ctx
            player = await interaction.user.voice.channel.connect(cls=Player, self_deaf=True)
        else:
            player = await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)  # type: ignore
    else:
        player = get_player(ctx)
    return player

async def play_music(ctx: commands.Context, track_name: str, source: TrackSource | str = None):
    if not ctx.interaction:
        await ctx.message.add_reaction(CHECKMARK)
    if "https://" not in track_name:
        ytsearch = YoutubeSearch(track_name, 1).to_dict()[0]
        track_name = f"https://youtu.be/{ytsearch['id']}"
        tracks: wavelink.Search = await Playable.search(track_name)
    else:
        tracks: wavelink.Search = await Playable.search(track_name, source=source)
    if not tracks:
        return await ctx.reply(embed=ErrorEmbed(f"Không tìm thấy kết quả nào cho `{track_name}`"))
    await add_to_queue(ctx, tracks[0])


class SelectTrackView(ui.View):
    def __init__(self, yt_tracks: list[Playable], sc_tracks: list[Playable]):
        super().__init__(timeout=180)
        self.message: Message | None = None
        self.add_item(SelectTrack(yt_tracks=yt_tracks, sc_tracks=sc_tracks))

    async def on_timeout(self) -> None:
        self.stop()
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)


class SelectTrack(ui.Select):
    def __init__(self, yt_tracks: list[Playable], sc_tracks: list[Playable]):
        super().__init__(
            placeholder="Chọn bài hát",
            options=[]
        )
        self.tracks = yt_tracks + sc_tracks

        for i, track in enumerate(yt_tracks):
            self.options.append(
                discord.SelectOption(
                    label=f"{str(i + 1)}. (YT) {textwrap.shorten(track.title, width=50, break_long_words=False, placeholder="...")}",
                    value=str(i)
                )
            )
        for i, track in enumerate(sc_tracks):
            self.options.append(
                discord.SelectOption(
                    label=f"{str(i + 1)}. (SC) {textwrap.shorten(track.title, width=50, break_long_words=False, placeholder="...")}",
                    value=str(i+len(yt_tracks))
                )
            )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.view.message = None
        await add_to_queue(interaction, self.tracks[int(self.values[0])])


class PlayerEmbed(FooterEmbed):
    """
    Embed cập nhật mỗi khi bài hát mới được phát.
    """
    def __init__(self, track: Playable):
        super().__init__(title=f"Đang phát: **{track}**")
        self.url = track.uri or None
        self.set_author(name=track.author, icon_url=PLAYING_GIF)
        self.set_thumbnail(url=track.artwork)
        

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
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.music_channel: discord.TextChannel

    async def cog_load(self) -> None:
        node = Node(uri=LAVA_URI, password=LAVA_PW, heartbeat=5.0, retries=1)
        await Pool.connect(client=self.bot, nodes=[node])
        self.music_channel = self.bot.get_channel(MUSIC_CHANNEL)
        if not self.music_channel:
            self.music_channel = await self.bot.fetch_channel(MUSIC_CHANNEL)

    async def cog_unload(self) -> None:
        await Pool.close()

    async def cog_check(self, ctx: commands.Context) -> bool:
        embed = ErrorEmbed()
        if not self._is_connected(ctx):
            embed.description = "Bạn cần tham gia kênh thoại để sử dụng lệnh"
            await ctx.reply(embed=embed, ephemeral=True)
            return False
        if not self._is_in_music_channel(ctx):
            embed.description = f"Lệnh này chỉ có thể dùng được ở <#{MUSIC_CHANNEL}>"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_same_channel(ctx):
            embed.description = (f"Bạn và {ctx.me.mention} phải cùng ở một kênh thoại.\n"
                                 f"{ctx.me.mention} đang ở kênh {ctx.guild.me.voice.channel.mention}")
            await ctx.reply(embed=embed, ephemeral=True)
            return False
        return True

    @staticmethod
    def _is_connected(ctx: commands.Context) -> bool:
        """
        Kiểm tra người dùng đã kết nối chưa
        """
        return ctx.author.voice is not None

    @staticmethod
    def _is_in_music_channel(ctx: commands.Context) -> bool:
        """
        Kiểm tra tin nhẵn có đang ở kênh lệnh bật nhạc không
        """
        return ctx.message.channel.id == MUSIC_CHANNEL

    @staticmethod
    def _is_in_same_channel(ctx: commands.Context) -> bool:
        """
        Kiểm tra xem bot và người dùng có ở cùng một kênh thoại hay không
        """
        bot_connected = ctx.guild.me.voice
        # Nếu bot không trong kênh thoại nào thì trả về True
        if not bot_connected:
            return True
        return bot_connected.channel.id == ctx.author.voice.channel.id

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload):
        """
        Xử lý khi bài hát kết thúc.
        """
        player: Player = payload.player
        if hasattr(player, "queue"):
            if not player.queue.is_empty:
                await player.play(player.queue.get(), populate=True, volume=50)
        else:
            await update_activity(self.bot)
            embed = FooterEmbed(title="Không còn bài hát nào trong hàng chờ")
            await self.music_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload):
        """
        Xử lý khi bài hát bắt đầu.
        """
        player: Player = payload.player
        await update_activity(self.bot, player.current.title)
        embed = PlayerEmbed(track=player.current)
        await self.music_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: TrackExceptionEventPayload):
        player: Player = payload.player
        track: Playable = player.current
        embed: Embed = ErrorEmbed(f"Có lỗi xuất hiện khi đang phát {track.title}\n"
                                  f"Chi tiết lỗi:\n"
                                  f"```\n"
                                  f"{payload.exception}\n"
                                  f"```")
        await self.music_channel.send(embed=embed)

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
    async def play_youtube(self, ctx: commands.Context, *, query: str):
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
    async def play_youtube_music(self, ctx: commands.Context, *, query: str):
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
    async def play_soundcloud(self, ctx: commands.Context, *, query: str):
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
    async def search(self, ctx: commands.Context, *, query: str):
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
            return msg.edit(embed=ErrorEmbed(f"Không tìm thấy kết quả nào cho `query`"))
        else:
            await msg.edit(embed=FooterEmbed(title=f"Kết quả tìm kiếm cho `{query}`"), view=view)

    @commands.hybrid_command(name='pause', description="Tạm dừng việc phát nhạc")
    async def pause_playing(self, ctx: commands.Context) -> None:
        player = get_player(ctx)
        await player.pause(True)
        embed = FooterEmbed(
            title="Đã tạm dừng chơi nhạc", 
            description="Dùng `!resume` hoặc `/resume` để tiếp tục"
            )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='resume', description="Tiếp tục việc phát nhạc")
    async def resume_playing(self, ctx: commands.Context) -> None:
        player: Player = get_player(ctx)
        await player.pause(False)
        embed = FooterEmbed(
            title="Đã tiếp tục chơi nhạc", 
            description="Dùng `!pause` hoặc `/pause` để tạm dừng"
            )
        await ctx.reply(embed=embed)

    @commands.hybrid_group(name='autoplay', aliases=['auto'], description="Bật hoặc tắt tự động phát.")
    async def autoplay_switch(self, ctx: commands.Context):
        """
        Bật hoặc tắt tự động phát.
        """
        player: Player = get_player(ctx)
        switch_to_mode: str = "bật" if player.autoplay == AutoPlayMode.disabled else "tắt"
        if player.autoplay == AutoPlayMode.enabled:
            player.autoplay = AutoPlayMode.disabled
        else:
            player.autoplay = AutoPlayMode.enabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã {switch_to_mode} chế độ tự động phát"))

    @autoplay_switch.command(name='on', description="Bật tính năng tự động phát")
    async def autoplay_on(self, ctx: commands.Context):
        """
        Bật tính năng tự động phát.
        """
        player = get_player(ctx)
        player.autoplay = AutoPlayMode.enabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã bật chế độ tự động phát"))

    @autoplay_switch.command(name='off', description="Tắt tính năng tự động phát")
    async def autoplay_off(self, ctx: commands.Context):
        """
        Tắt tính năng tự động phát.
        """
        player = get_player(ctx)
        player.autoplay = AutoPlayMode.disabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã tắt chế độ tự động phát"))

    @commands.hybrid_command(name='nowplaying',
                             aliases=['np', 'now', 'current'],
                             description="Đang phát bài gì thế?")
    async def nowplaying(self, ctx: commands.Context):
        player = get_player(ctx)
        if player.playing:
            track = player.current
            embed = FooterEmbed(
                title=track,
                description=f"**Độ dài**: {length_convert(track)}",
            )
            embed.url = track.uri
            if track.artwork:
                embed.set_image(url=track.artwork)
            embed.set_author(name=track.author)
        else:
            embed = ErrorEmbed("Hiện đang không phát bất cứ thứ gì")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='skip', description="Bỏ qua bài hát hiện tại.")
    async def skip(self, ctx: commands.Context):
        player = get_player(ctx)
        track = player.current
        if track:
            embed = Embed().set_author(name=f"Đã skip {track}", icon_url=SKIP_EMOJI)
            await player.seek(track.length)
        else:
            embed = ErrorEmbed("Hiện đang không phát bất cứ thứ gì")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='stop', description="Dừng phát nhạc và xóa hàng chờ")
    async def stop_playing(self, ctx: commands.Context):
        player = get_player(ctx)
        player.queue.clear()
        await player.stop(force=True)
        embed = Embed().set_author(name=f"Đã dừng phát nhạc và xóa toàn bộ hàng chờ", icon_url=SKIP_EMOJI)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='queue', aliases=['q'], description="Xem chi tiết hàng chờ.")
    async def queue_command(self, ctx: commands.Context):
        await self._show_queue(ctx)

    async def _show_queue(self, ctx: commands.Context):
        embeds: list[Embed] | Embed = self._queue_embeds(ctx)
        if isinstance(embeds, Embed):
            return await ctx.reply(embed=embeds)
        view = QueueView(embeds)
        view.message = await ctx.reply(embed=embeds[0], view=view)

    def _queue_embeds(self, ctx: commands.Context) -> list[Embed] | Embed:
        player = get_player(ctx)
        if player.queue.is_empty:
            embed: Embed = FooterEmbed(title="Hàng chờ trống!")
            return embed
        queue_embeds: list[Embed] = []
        q: str = ""
        for i, track in enumerate(player.queue, 1):
            q += f"{i}. [**{track}**](<{track.uri}>) ({length_convert(track)})\n"
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
                value=f"[**{track}**](<{track.uri}>) ({length_convert(track)})"
                )
        return embed

    @commands.hybrid_command(name='delete', aliases=['rm', 'remove'], description="Xóa một bài hát khỏi hàng chờ.")
    async def remove(self, ctx: commands.Context, number: Optional[int] = 0):
        """
        Xóa một bài hát khỏi hàng chờ.

        Parameters
        -----------
        ctx
            commands.Context
        number
            Số thứ tự bài hát trong hàng chờ, bỏ trống hoặc điền số 0 để xóa bài hát vừa đặt
        """
        player = get_player(ctx)
        if number < 0 or number > player.queue.count:
            return
        else:
            track_index = player.queue.count - 1 if number == 0 else number - 1
            deleted = player.queue[track_index]
            del player.queue[track_index]
            await ctx.send(embed=Embed(title=f"Đã xóa {deleted} khỏi hàng chờ."))
            await self._show_queue(ctx)

    @commands.hybrid_command(name='connect', aliases=['j', 'join'], description="Kết nối bot vào kênh thoại.")
    async def connect_command(self, ctx: commands.Context):
        player = await ensure_voice_connection(ctx)
        embed = AvatarEmbed(
            title="— Đã kết nối!",
            desc=f"Đã vào kênh {player.channel.mention}.",
            user=ctx.author
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='disconnect', aliases=['dc', 'leave', 'l'], description="Ngắt kết nối bot khỏi kênh thoại.")
    async def disconnect_command(self, ctx: commands.Context):
        if ctx.voice_client:
            embed = AvatarEmbed(
                title="— Đã ngắt kết nối!",
                desc=f"Đã rời kênh {ctx.voice_client.channel.mention}",
                user=ctx.author
            )
            await ctx.voice_client.disconnect(force=True)
            await update_activity(self.bot)
        else:
            embed = ErrorEmbed("Bot không nằm trong kênh thoại nào.")
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))
