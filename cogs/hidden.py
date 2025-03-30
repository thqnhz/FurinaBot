from __future__ import annotations

import io
from typing import Optional, Tuple, TYPE_CHECKING


import discord
from discord.ext import commands
from discord import app_commands, Embed, Color


from settings import *


if TYPE_CHECKING:
    from bot import FurinaBot


class SendEmbedView(discord.ui.View):
    def __init__(self, embed: Embed, channel: discord.TextChannel = None):
        super().__init__(timeout=None)
        self.channel = channel
        self.embed = embed

    @discord.ui.button(label="Send", emoji="💭")
    async def send_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        if self.channel:
            await self.channel.send(embed=self.embed)
        else:
            await interaction.channel.send(embed=self.embed)


class Hidden(commands.Cog):
    """Hidden Commands"""
    def __init__(self, bot: FurinaBot):
        self.bot = bot

    @app_commands.command(name='embed', description="Send an embed.")
    @app_commands.default_permissions(manage_permissions=True)
    async def send_embed(self, interaction: discord.Interaction,
                         title: str, *, url: Optional[str] = None,
                         desc: Optional[str] = None,
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
        Send an embed.

        Parameters
        -----------
        title
            - The embed title
        url
            - Embed url
        desc
            - Embed description
        author
            - Author text
        thumbnail
            - Thumbnail (file)
        image
            - Big image (file)
        channel
            - Destination channel
        footer
            - Embed footer text
        field1
            First field name
        field1_value
            First field value
        field2
            Second field name
        field2_value
            Second field value
        field3
            Third field name
        field3_value
            Third field value
        """

        embed = Embed(title=title,
                      description=desc.replace("\\n", "\n") if desc else None,
                      color=Color.blue(),
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


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Hidden(bot))

