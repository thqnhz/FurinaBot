import discord, wavelink, functools
from discord.ext import commands
from discord import Color, Embed
from discord.ui import Button
from discord import Message
from typing import Type, cast
from wavelink import (Player, Playable, Playlist, TrackSource, Node, Pool, TrackStartEventPayload,
                      TrackEndEventPayload, TrackExceptionEventPayload, NodeStatus, AutoPlayMode)

# Custom subclasses
from _classes.embeds import *
from _classes.views import *
from _classes.buttons import *
from settings import *
from helper import *


class QueueView(discord.ui.View):
    def __init__(self, embeds: list[Embed]):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.page: int = 0
        self.message: Message | None = None
        if len(self.embeds) == 1:
            self.next_button.disabled = True

    @discord.ui.button(emoji="\u25c0", disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page == 0:
            button.disabled = True
        self.next_button.disabled = False
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(emoji="\u25b6")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        self.player_channel = self.bot.get_channel(PLAYER_CHANNEL)
        self.player_message: Message | None = None

    async def cog_load(self) -> None:
        node: Node = Node(uri=LAVA_URI, password=LAVA_PW, heartbeat=5.0, retries=1)
        # Kết nối với Lavalink Node
        await Pool.connect(client=self.bot, nodes=[node])
        # Tìm tin nhắn đầu tiên chứa embed của kênh player
        if not self.player_channel:
            self.player_channel = await self.bot.fetch_channel(PLAYER_CHANNEL)
        async for message in self.player_channel.history(limit=1):
            self.player_message = message
            break

    async def cog_unload(self) -> None:
        await Pool.close()

    async def cog_check(self, ctx: commands.Context) -> bool:
        embed: Embed = ErrorEmbed()
        if not self._is_connected(ctx):
            embed.description = "Bạn cần tham gia kênh thoại để sử dụng lệnh"
            await ctx.reply(embed=embed, ephemeral=True)
            return False
        if not self._is_in_music_channel(ctx):
            embed.description = f"Lệnh này chỉ có thể dùng được ở <#{MUSIC_CHANNEL}>"
            await ctx.reply(embed=embed, ephemeral=True, delete_after=10)
            return False
        if not self._is_in_same_channel(ctx):
            embed.description = (f"Bạn và {ctx.me.display_name} phải cùng ở một kênh thoại.\n"
                                 f"{ctx.me.display_name} đang ở kênh {ctx.guild.me.voice.channel.mention}")
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

    @staticmethod
    def get_player(ctx: commands.Context) -> Player:
        """
        Lấy voice_client
        """
        return cast(Player, ctx.guild.voice_client)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload):
        """
        Xử lý khi bài hát kết thúc.
        """
        player: Player = payload.player
        if not player.queue.is_empty:
            await player.play(player.queue.get(), populate=True, volume=50)
        else:
            await update_activity(self.bot)
            embed: Embed = FooterEmbed(title="Không còn bài hát nào trong hàng chờ")
            await update_player_embed(embed=embed, msg=self.player_message, channel=self.player_channel)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload):
        """
        Xử lý khi bài hát bắt đầu.
        """
        player: Player = payload.player
        await update_activity(self.bot, player.current.title)
        embed: Embed = PlayerEmbed(track=player.current)
        view = PlayerView(vc=player)
        await update_player_embed(embed=embed, msg=self.player_message, channel=self.player_channel, view=view)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: TrackExceptionEventPayload):
        player: Player = payload.player
        track: Playable = player.current
        embed: Embed = ErrorEmbed(f"Có lỗi xuất hiện khi đang phát {track.title}\n"
                                  f"Chi tiết lỗi:\n"
                                  f"```\n"
                                  f"{payload.exception}\n"
                                  f"```")
        channel = self.bot.get_channel(MUSIC_CHANNEL)
        await channel.send(embed=embed)

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
        await self._play_music(ctx, query, TrackSource.YouTubeMusic)

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
        await self._play_music(ctx, query)

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
        await self._play_music(ctx, query, TrackSource.YouTubeMusic)

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
        await self._play_music(ctx, query, TrackSource.SoundCloud)

    async def _play_music(self,
                          ctx: commands.Context,
                          track_name: str,
                          source: TrackSource | str = None):
        if not ctx.interaction:
            await ctx.message.add_reaction(CHECKMARK)
        tracks: wavelink.Search = await Playable.search(track_name, source=source)
        if not tracks:
            return await ctx.reply(embed=ErrorEmbed(f"Không tìm thấy kết quả nào cho `{track_name}`"))
        await self._add_to_queue(ctx, tracks)

    async def _add_to_queue(self, ctx: commands.Context, data: Playlist | list[Playable]):
        msg = await ctx.reply(embed=LoadingEmbed())
        player: Player = await self._ensure_voice_connection(ctx)

        # Kiểm tra xem bot có đang ở trong StageChannel không để có thể request to speak
        if isinstance(player.channel, discord.StageChannel):
            await player.channel.guild.me.edit(suppress=False)

        async with ctx.channel.typing():
            if isinstance(data, Playlist):
                await self._add_a_playlist(ctx, data, msg)
            else:
                await self._add_a_song(ctx, data[0], msg)

    async def _ensure_voice_connection(self, ctx: commands.Context) -> Player:
        player: Player
        if not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)  # type: ignore
        else:
            player = self.get_player(ctx)
        return player

    async def _add_a_song(self, ctx: commands.Context, track: Playable, msg: Message):
        """
        Thêm một bài hát vào hàng chờ.
        """
        if not self._track_check(track):
            return await ctx.reply(embed=ErrorEmbed("""Bài hát bạn yêu cầu dài hơn 1 tiếng hoặc là bạn đang yêu cầu 
            một livestream. Vui lòng chọn bài khác.
            """))
        player = self.get_player(ctx)
        await player.queue.put_wait(track)
        bookers[track.title] = ctx.author.id
        embed: Embed = FooterEmbed(title="— Đã thêm vào hàng chờ", color=Color.green())
        if track.artwork:
            embed.set_image(url=track.artwork)
            embed.set_author(name=track.author)
        embed.add_field(name="Tên bài hát", value=f"[**{track}**](<{track.uri}>)")
        embed.add_field(name="Độ dài", value=f"{self._track_len_format(track)}")
        if player.playing:
            embed.add_field(name="Thứ tự hàng chờ", value=f"{player.queue.count}")
        else:
            await player.play(player.queue.get(), populate=True, volume=50)
        await msg.edit(embed=embed)

    async def _add_a_playlist(self, ctx: commands.Context, tracks: Playlist, msg: Message):
        """
        Thêm một playlist vào hàng chờ.
        """
        track_count: int = 0
        embed: Embed = FooterEmbed(title=f"Đã thêm {track_count} bài hát vào hàng chờ", description="")
        player: Player = self.get_player(ctx)
        for track in tracks:
            if self._track_check(track):
                embed.description += f"- Đã thêm `{track}` vào hàng chờ\n"
                await player.queue.put_wait(track)
                bookers[track.title] = ctx.author.id
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

    @staticmethod
    def _track_check(track: Playable):
        if hasattr(track, "is_stream"):
            if track.is_stream:
                return False
        return track.length // HOUR < 1

    @staticmethod
    def _track_len_format(track: Playable):
        """
        Chuyển đổi độ dài track sang dạng đọc được.
        """
        return '{:02}:{:02}'.format(*divmod(track.length // 1000, 60))

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
        tracks_yt: wavelink.Search = await Playable.search(query, source=TrackSource.YouTubeMusic)
        tracks_sc = await Playable.search(query, source=TrackSource.SoundCloud)

        tracks = tracks_yt[:5] + tracks_sc[:5]

        if len(tracks) == 0:
            return ctx.reply(embed=ErrorEmbed(f"Không tìm thấy kết quả nào cho `query`"))
        else:
            view = TimeoutView()

            async def select_track(interaction: discord.Interaction, t):
                await interaction.response.defer()
                if interaction.user.id == ctx.author.id:
                    await self._ensure_voice_connection(ctx)
                    await msg.edit(embed=LoadingEmbed(), view=None)
                    await self._add_a_song(ctx, t, msg)
                else:
                    await interaction.followup.send(embed=ErrorEmbed("Chỉ có người dùng lệnh này mới có thể chọn!"))

            for i, track in enumerate(tracks, 0):
                button = Button(
                    label=str(i % 5 + 1),
                    emoji='<:sc:1162335003678625832>' if (i >= 5) else
                    '<:yt:1162334665387032627>',
                    row=1 if (i >= 5) else 0
                )
                button.callback = functools.partial(select_track, t=track)
                view.add_item(button)

            embed = Embed(title=f"Kết quả tìm kiếm cho `{query}`")
            yt = get_track_list(tracks_yt[:5])
            sc = get_track_list(tracks_sc[:5])
            embed.add_field(name="YouTube Music", value=yt)
            embed.add_field(name="SoundCloud", value=sc)
            embed.set_footer(text="Vui lòng chọn bài hát.")
            view.message = await msg.edit(embed=embed, view=view)

    @commands.hybrid_command(name='pause', description="Tạm dừng việc phát nhạc")
    async def pause_playing(self, ctx: commands.Context) -> None:
        player = self.get_player(ctx)
        await player.pause(True)
        embed = FooterEmbed(title="Đã tạm dừng chơi nhạc", description="Dùng `!resume hoặc /resume để tiếp tục")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='resume', description="Tiếp tục việc phát nhạc")
    async def resume_playing(self, ctx: commands.Context) -> None:
        player: Player = self.get_player(ctx)
        await player.pause(False)
        embed = FooterEmbed(title="Đã tiếp tục chơi nhạc", description="Dùng `!pause hoặc /pause để tạm dừng")
        await ctx.reply(embed=embed)

    @commands.hybrid_group(name='autoplay', aliases=['auto'], description="Bật hoặc tắt tự động phát.")
    async def autoplay_switch(self, ctx: commands.Context):
        """
        Bật hoặc tắt tự động phát.
        """
        player: Player = self.get_player(ctx)
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
        player = self.get_player(ctx)
        player.autoplay = AutoPlayMode.enabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã bật chế độ tự động phát"))

    @autoplay_switch.command(name='off', description="Tắt tính năng tự động phát")
    async def autoplay_off(self, ctx: commands.Context):
        """
        Tắt tính năng tự động phát.
        """
        player = self.get_player(ctx)
        player.autoplay = AutoPlayMode.disabled
        await ctx.reply(embed=FooterEmbed().set_author(name=f"Đã tắt chế độ tự động phát"))

    @commands.hybrid_command(name='nowplaying',
                             aliases=['np', 'now', 'current'],
                             description="Đang phát bài gì thế?")
    async def nowplaying(self, ctx: commands.Context):
        vc = self.get_player(ctx)
        if vc.playing:
            track = vc.current
            embed = FooterEmbed(
                title=track,
                description=f"**Độ dài**: {self._track_len_format(track)}",
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
        vc = self.get_player(ctx)
        track = vc.current
        if track:
            embed = Embed().set_author(name=f"Đã skip {track}", icon_url=SKIP_EMOJI)
            await vc.seek(track.length)
        else:
            embed = ErrorEmbed("Hiện đang không phát bất cứ thứ gì")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='stop', description="Dừng phát nhạc và xóa hàng chờ")
    async def stop_playing(self, ctx: commands.Context):
        vc = self.get_player(ctx)
        vc.queue.clear()
        await vc.stop(force=True)
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
        player = self.get_player(ctx)
        if player.queue.is_empty:
            embed: Embed = FooterEmbed(title="Hàng chờ trống!")
            return embed
        queue_embeds: list[Embed] = []
        q: str = ""
        for i, track in enumerate(player.queue, 1):
            q += f"{i}. [**{track}**](<{track.uri}>) ({self._track_len_format(track)})\n"
            if i % 5 == 0:
                embed: Embed = self._create_queue_embed(player, q)
                queue_embeds.append(embed)
                q = ""
        if q:
            embed: Embed = self._create_queue_embed(player, q)
            queue_embeds.append(embed)
        return queue_embeds

    def _create_queue_embed(self, player: Player, q: str) -> Embed:
        embed: Embed = FooterEmbed(color=Color.blue(),
                                   title=f"Hàng chờ: {player.queue.count} bài hát",
                                   description=q)
        if player.playing:
            track = player.current
            embed.add_field(name="Đang phát",
                            value=f"[**{track}**](<{track.uri}>) ({self._track_len_format(track)})")
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
        vc: Player = ctx.guild.voice_client  # type: ignore
        if number < 0 or number > vc.queue.count:
            return
        else:
            track_index = vc.queue.count - 1 if number == 0 else number - 1
            deleted = vc.queue[track_index]
            del vc.queue[track_index]
            del bookers[deleted.title]
            await ctx.send(embed=Embed(title=f"Đã xóa {deleted} khỏi hàng chờ."))
            await self._show_queue(ctx)

    @commands.hybrid_command(name='connect',
                             aliases=['j', 'join'],
                             description="Kết nối bot vào kênh thoại.")
    async def connect(self, ctx: commands.Context):
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)  # type: ignore
            embed = AvatarEmbed(
                title="— Đã kết nối!",
                desc=f"Đã vào kênh {ctx.voice_client.channel.mention}.",
                user=ctx.author
            )
        else:
            embed = ErrorEmbed(f"Bot đang ở kênh {ctx.voice_client.channel.mention}.\n"
                               f"Hãy vào kênh này để có thể sử dụng bot")
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name='disconnect',
                             aliases=['dc', 'leave', 'l'],
                             description="Ngắt kết nối bot khỏi kênh thoại.")
    async def disconnect(self, ctx: commands.Context):
        if ctx.voice_client:
            embed = AvatarEmbed(
                title="— Đã ngắt kết nối!",
                desc=f"Đã rời kênh {ctx.voice_client.channel.mention}",
                user=ctx.author
            )
            await ctx.voice_client.disconnect(force=True)
            await update_activity(self.bot)
            player_embed = FooterEmbed(title="Không còn bài hát nào trong hàng chờ")
            await update_player_embed(embed=player_embed, msg=self.player_message, channel=self.player_channel)
        else:
            embed = ErrorEmbed("Bot không nằm trong kênh thoại nào.")
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))
