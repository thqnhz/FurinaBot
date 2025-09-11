"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord import ButtonStyle, Embed, Interaction, ui

from .base import View

if TYPE_CHECKING:
    from discord.ui import Button


class PaginatedView(View):
    def __init__(self, *, timeout: float, embeds: list[Embed] | Embed) -> None:
        super().__init__(timeout=timeout)
        self.embeds = embeds if isinstance(embeds, list) else [embeds]
        self.title: list[str] = [embed.title for embed in self.embeds]  # type: ignore[reportAttributeAccessIssue]
        self.length: int = len(self.embeds)
        self.page: int = 0
        self.page_button.label = self.page_button_label
        if len(self.embeds) == 1:
            self.clear_items()

    @property
    def page_button_label(self) -> str:
        return f"{self.title[self.page]} ({self.page + 1}/{self.length})"

    def update_buttons(self) -> None:
        self.first_button.disabled = self.page == 0
        self.left_button.disabled = self.page == 0
        self.page_button.label = self.page_button_label
        self.right_button.disabled = self.page == self.length - 1
        self.last_button.disabled = self.page == self.length - 1

    @ui.button(label="<<", disabled=True)  # type: ignore[reportArgumentType]
    async def first_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page = 0
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)

    @ui.button(label="<", disabled=True)  # type: ignore[reportArgumentType]
    async def left_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page -= 1
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)

    @ui.button(style=ButtonStyle.blurple, disabled=True)  # type: ignore[reportArgumentType]
    async def page_button(self, _: Interaction, __: Button) -> None:
        pass

    @ui.button(label=">")  # type: ignore[reportArgumentType]
    async def right_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page += 1 if self.page <= self.length - 1 else self.page
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)

    @ui.button(label=">>")  # type: ignore[reportArgumentType]
    async def last_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page = self.length - 1
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)
