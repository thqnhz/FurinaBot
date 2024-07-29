import json

import discord
from discord import ButtonStyle
from discord.ui import View, Button, Modal, Select

from _classes.buttons import *
import settings
from settings import bookers


class TimeoutView(View):
    """
    View chung có xử lý timeout
    """
    def __init__(self, timeout=60.0):
        super().__init__(timeout=timeout)
  
    async def on_timeout(self):
        try:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
        except discord.NotFound:
            pass


class ButtonView(View):
    """
    View cho Button
    """
    def __init__(self, timeout=60.0):
        super().__init__(timeout=timeout)
      
    async def on_timeout(self):
        for item in self.children:
            item.label = "ĐÃ TẮT VÌ TIMEOUT"
            item.style = ButtonStyle.secondary
            item.emoji = '❌'
            item.disabled = True
        await self.message.edit(view=self)


class SelectView(View):
    """
    View cho Select
    """
    def __init__(self, timeout=60.0):
        super().__init__(timeout=timeout)

    async def on_timeout(self):
        for item in self.children:
            item.placeholder = "❌ ĐÃ TẮT VÌ TIMEOUT"
            item.disabled = True
        await self.message.edit(view=self)


class PlayerView(View):
    """
    View cho kênh điều khiển player.
    """
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @discord.ui.button(emoji="<:stop:1221490994923442266>", custom_id="player:stop")
    async def stop_button(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        for role in interaction.user.roles:
            if role.name == "DJ":
                self.vc.queue.clear()
                await self.vc.stop()
                return
        await interaction.followup.send(embed=ErrorEmbed("Chỉ có ai có role DJ mới có thể buộc dừng chơi nhạc!"))

    @discord.ui.button(emoji="<:playpause:1222556825698959410>", custom_id="player:pauseplay")
    async def pause_button(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if self.vc.is_playing() is True:
            await self.vc.pause()
        elif self.vc.is_paused() is True:
            await self.vc.resume()
        else:
            await interaction.followup.send(embed=ErrorEmbed("Hiện đang không phát thứ gì"), ephemeral=True)

    @discord.ui.button(emoji="<:next:1222558976676335676>", custom_id="player:next")
    async def next_button(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        for role in interaction.user.roles:
            if role.name == "DJ":
                del bookers[self.vc.current.title]
                await self.vc.seek(self.vc.current.length)
                return

        if interaction.user.id == bookers[self.vc.current.title]:
            del bookers[self.vc.current.title]
            await self.vc.seek(self.vc.current.length)
            return
        else:
            needed = len(self.vc.channel.members) // 2
            if len(settings.skippers) >= needed:
                del bookers[self.vc.current.title]
                await self.vc.seek(self.vc.current.length)
                settings.skippers = []  # Đặt lại biến skippers về danh sách rỗng
                return
            elif interaction.user.id in settings.skippers:
                await interaction.followup.send(
                    embed=ErrorEmbed(f"Bạn đã vote skip rồi. Cần thêm {needed - len(settings.skippers)} vote để skip."),
                    ephemeral=True
                )
            else:
                settings.skippers.append(interaction.user.id)
                await interaction.followup.send(
                    embed=discord.Embed(
                        title=f"Đã vote skip thành công! Cần thêm {needed - len(settings.skippers)} vote để skip."
                    ),
                    ephemeral=True
                )

    @discord.ui.button(emoji="<:queue:1222558678796730469>", custom_id="player:queue")
    async def queue_button(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = FooterEmbed(title=f"Hàng chờ: {self.vc.queue.count}", description="")
        for i, track in enumerate(self.vc.queue, 1):
            embed.description += f"{i}. [**{track}**](<{track.uri}>)\n"
        await interaction.followup.send(embed=embed, ephemeral=True)




