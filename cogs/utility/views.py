from __future__ import annotations

from typing import List

from discord import ui, Button, Embed, Interaction, Message


class View(ui.View):
    """A View that auto disable children when timed out"""
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
        self.message: Message

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)


class PaginatedView(View):
    def __init__(self, *, timeout: float, embeds: List[Embed]):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.page: int = 0
        if len(self.embeds) == 1:
            self.clear_items()

    @ui.button(emoji="\U00002b05", disabled=True)
    async def left_button(self, interaction: Interaction, button: Button):
        self.page -= 1
        button.disabled = True if self.page == 0 else False
        self.right_button.disabled = False
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @ui.button(emoji="\U000027a1")
    async def right_button(self, interaction: Interaction, button: Button):
        self.page += 1 if self.page <= len(self.embeds) - 1 else self.page
        button.disabled = True if self.page == len(self.embeds) - 1 else False
        self.left_button.disabled = False
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)
        