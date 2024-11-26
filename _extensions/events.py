import discord, traceback
from discord import Embed
from discord.ext import commands
from typing import TYPE_CHECKING


from settings import MUSIC_CHANNEL
from _extensions.music import update_activity
from _classes.embeds import ErrorEmbed, FooterEmbed

if TYPE_CHECKING:
    from bot import Furina


class BotEvents(commands.Cog):
    def __init__(self, bot: "Furina") -> None:
        self.bot = bot

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
        else:
            embed.description = f"{error}"
        await ctx.reply(embed=embed, ephemeral=True, delete_after=60)

        traceback.print_exception(error)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        player_channel = before.channel
        if player_channel and not after.channel:
            if len(player_channel.members) == 1 and player_channel.members[0] == self.bot.user:
                await member.guild.voice_client.disconnect(force=True)
                channel = self.get_channel(MUSIC_CHANNEL)
                embed = FooterEmbed(title="Đừng bỏ mình một mình trong kênh, mình sợ :fearful:")
                embed.set_image(url="https://media1.tenor.com/m/Cbwh3gVO4KAAAAAC/genshin-impact-furina.gif")
                await channel.send(embed=embed)
                await update_activity(self)


async def setup(bot: "Furina"):
    await bot.add_cog(BotEvents(bot))

