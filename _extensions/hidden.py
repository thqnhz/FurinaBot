import discord, io, subprocess
from discord.ext import commands
from discord import app_commands, Embed, Color
from typing import TYPE_CHECKING, Literal, Optional


from settings import *
from _classes.embeds import *

if TYPE_CHECKING:
    from bot import Furina


class SendEmbedView(discord.ui.View):
    def __init__(self, embed: Embed, channel: discord.TextChannel = None):
        super().__init__(timeout=None)
        self.channel = channel
        self.embed = embed

    @discord.ui.button(label="Gửi", emoji="💭")
    async def send_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        if self.channel:
            await self.channel.send(embed=self.embed)
        else:
            await interaction.channel.send(embed=self.embed)


class Hidden(commands.Cog):
    """Lệnh ẩn"""
    def __init__(self, bot: "Furina"):
        self.bot = bot

    @commands.command(hidden=True, aliases=['ext', 'e'], description="Các hành động liên quan đến extension")
    @commands.is_owner()
    async def extension(self, ctx: commands.Context, action: Literal['l', 'u', 'r'], extension_name: str) -> None:
        embed: FooterEmbed = FooterEmbed(title="— Thành công!", color=Color.green())
        avatar_url = ctx.author.avatar.url
        embed.set_thumbnail(url=avatar_url)

        action_mapping = {
            'l': self.bot.load_extension,
            'u': self.bot.unload_extension,
            'r': self.bot.reload_extension
        }
        action_fullname_mapping = {
            'l': "load",
            'u': "unload",
            'r': "reload"
        }

        try:
            method = action_mapping.get(action)
            action = action_fullname_mapping.get(action)
            await method(f'_extensions.{extension_name}')
            embed.description = f"Đã {action} extension {extension_name}"
        except Exception as e:
            embed = ErrorEmbed(f"{e}")
        await ctx.reply(embed=embed, delete_after=5)
        await ctx.message.delete()

    @commands.command(hidden=True, name='reboot', aliases=['restart'], description="Khởi động lại bot.")
    @commands.is_owner()
    async def reboot(self, ctx: commands.Context) -> None:
        embed = LoadingEmbed(author_name="Đang khởi động lại...")
        msg = await ctx.reply(embed=embed)
        try:
            subprocess.run(REBOOT_CMD, shell=True)
        except Exception as e:
            embed = ErrorEmbed(f"Có lỗi xảy ra khi khởi động lại: {e}")
            await msg.edit(embed=embed, delete_after=5)

    @commands.command(hidden=True, name='logs', aliases=['log'], description="Lấy nhật ký từ console.")
    @commands.is_owner()
    async def logs(self, ctx: commands.Context, number: int = 15) -> None:
        process = subprocess.Popen(
            ['tail', LOG_FILE, f'-n {number}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output, errors = process.communicate()
        file = None

        if process.returncode == 0:
            embed = FooterEmbed(title=f"Nhật ký lỗi gần đây nhất của Furina ({number} dòng)",
                                description="")
            if len(output) < 4096 and number < 30:
                embed.description = f"```prolog\n{output}\n```"
            else:
                file = discord.File(fp=io.StringIO(output), filename=f'logs-{number}lines.log')
        else:
            embed = ErrorEmbed(description=f"Có lỗi xảy ra khi lấy nhật ký: {errors}")
        await ctx.reply(embed=embed, file=file)

    @app_commands.command(name='embed', description="Gửi một embed.")
    @app_commands.default_permissions(manage_permissions=True)
    async def send_embed(self, interaction: discord.Interaction,
                         title: str, *, url: Optional[str] = None,
                         desc: Optional[str] = None,
                         color: Optional[bool] = True,
                         author: Optional[str] = None,
                         thumbnail: Optional[discord.Attachment] = None,
                         image: Optional[discord.Attachment] = None,
                         channel: Optional[discord.TextChannel] = None,
                         footer: Optional[str] = None,
                         field1: Optional[str] = None,
                         field1_value: Optional[str] = None,
                         field2: Optional[str] = None,
                         field2_value: Optional[str] = None,
                         field3: Optional[str] = None,
                         field3_value: Optional[str] = None) -> None:
        """
        Gửi một embed.

        Parameters
        -----------
        interaction
            discord.Interaction
        title
            Tiêu đề của embed.
        url
            URL của embed.
        desc
            Description của embed.
        color
            Embed có màu hay không?
        author
            Chủ sở hữu embed (ở trên tiêu đề).
        thumbnail
            Ảnh thu nhỏ cho embed (File).
        image
            Ảnh to của embed (File).
        channel
            Kênh cần gửi embed vào
        footer
            Chân embed.
        field1
            Tiêu đề field thứ nhất của embed
        field1_value
            Giá trị field thứ nhất của embed
        field2
            Tiêu đề field thứ hai của embed
        field2_value
            Giá trị field thứ hai của embed
        field3
            Tiêu đề field thứ ba của embed
        field3_value
            Giá trị field thứ ba của embed
        """

        embed = Embed(title=title,
                      description=desc.replace("\\n", "\n") if desc else None,
                      color=Color.blue() if color else None,
                      url=url)
        if author:
            embed.set_author(name=author)
        if thumbnail:
            if hasattr(thumbnail, "url"):
                embed.set_thumbnail(url=thumbnail.url)
            else:
                embed.set_thumbnail(url=thumbnail)
        if image:
            if hasattr(image, "url"):
                embed.set_image(url=image.url)
            else:
                embed.set_image(url=thumbnail)
        embed.set_footer(text=footer) if footer else None
        if field1:
            embed.add_field(name=field1, value=field1_value if field1_value else "", inline=False)
        if field2:
            embed.add_field(name=field2, value=field2_value if field2_value else "", inline=False)
        if field3:
            embed.add_field(name=field3, value=field3_value if field3_value else "", inline=False)
        view: SendEmbedView = SendEmbedView(embed, channel)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)


async def setup(bot: "Furina"):
    await bot.add_cog(Hidden(bot))

