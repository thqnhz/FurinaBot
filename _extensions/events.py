import discord, traceback
from discord import Embed, Activity, ActivityType
from discord.ext import commands
from typing import TYPE_CHECKING
from wavelink import Player, Playable, TrackStartEventPayload, TrackEndEventPayload


from settings import MUSIC_CHANNEL, ACTIVITY_NAME
from _classes.embeds import ErrorEmbed, FooterEmbed

if TYPE_CHECKING:
    from bot import Furina


class BotEvents(commands.Cog):
    def __init__(self, bot: "Furina") -> None:
        self.bot = bot

    async def _update_activity(self, state: str = "N̸o̸t̸h̸i̸n̸g̸") -> None:
        """
        Cập nhật activity của bot theo bài hát đang phát.

        Parameters
        -----------
        bot: `commands.Bot`
            bot
        state: `str`
            Tên bài hát đang phát.
        """
        await self.bot.change_presence(activity=Activity(type=ActivityType.playing, name=ACTIVITY_NAME, state=f"Playing: {state}"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            pass

        # xử lý tin nhắn riêng
        if isinstance(message.channel, discord.DMChannel):
            if message.author != self.bot.user and message.author.id != self.bot.owner_id:
                owner = self.bot.get_user(self.bot.owner_id)
                if not owner:
                    owner = await self.bot.fetch_user(self.bot.owner_id)
                embed: Embed = Embed(
                    title=f"{message.author} ({message.author.id}) đã gửi một tin nhắn",
                    description="`" + message.content + "`" if message.content else None
                )
                embed.timestamp = message.created_at
                await owner.send(embed=embed)
                if message.attachments:
                    for attachment in message.attachments:
                        await owner.send(attachment.url)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.errors.CommandError) -> None:
        embed = ErrorEmbed()
        if isinstance(error, commands.CommandNotFound):
            embed.description = f"Không tìm thấy lệnh `{ctx.message.content.split()[0]}`"
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.description = f"Lệnh của bạn thiếu phần: `{error.param.name}`"
        elif isinstance(error, commands.CheckFailure):
            return
        else:
            embed.description = f"{error}"
        await ctx.reply(embed=embed, ephemeral=True, delete_after=60)
        
        traceback.print_exception(error)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        # thay đổi activity khi bot thoát kênh thoại
        if member == self.bot.user and not after.channel:
            await self._update_activity()

        # thoát kênh nếu là người duy nhất trong kênh
        if before.channel and not after.channel:
            if len(before.channel.members) == 1 and before.channel.members[0] == self.bot.user:
                await member.guild.voice_client.disconnect(force=True)
                channel = self.bot.get_channel(MUSIC_CHANNEL)
                embed = FooterEmbed(title="Đừng bỏ mình một mình trong kênh, mình sợ :fearful:")
                embed.set_image(url="https://media1.tenor.com/m/Cbwh3gVO4KAAAAAC/genshin-impact-furina.gif")
                await channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: TrackEndEventPayload):
        """Cập nhật activity khi track kết thúc."""
        player: Player = payload.player
        if player.queue.is_empty:
            await self._update_activity()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: TrackStartEventPayload):
        """Cập nhật activity khi track bắt đầu."""
        track: Playable = payload.track
        await self._update_activity(track.title)

async def setup(bot: "Furina"):
    await bot.add_cog(BotEvents(bot))

