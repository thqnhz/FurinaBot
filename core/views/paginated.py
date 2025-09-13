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

from .base import LayoutView, View

if TYPE_CHECKING:
    from discord.ui import Button

    from core.views import Container


class PaginatedView(View):
    def __init__(self, *, timeout: float, embeds: list[Embed] | Embed) -> None:
        super().__init__(timeout=timeout)
        self.embeds = embeds if isinstance(embeds, list) else [embeds]
        self.title: list[str] = [embed.title for embed in self.embeds]
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

    @ui.button(label="<<", disabled=True)
    async def first_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page = 0
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)

    @ui.button(label="<", disabled=True)
    async def left_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page -= 1
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)

    @ui.button(style=ButtonStyle.blurple, disabled=True)
    async def page_button(self, _: Interaction, __: Button) -> None:
        pass

    @ui.button(label=">")
    async def right_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page += 1 if self.page <= self.length - 1 else self.page
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)

    @ui.button(label=">>")
    async def last_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        self.page = self.length - 1
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.page], view=self)


class PaginateActionRow(ui.ActionRow):
    def __init__(self, page: int, length: int) -> None:
        super().__init__()
        self.page = page
        self.length = length
        self.page_button.label = self.page_button_label
        if self.page == 0:
            self.first_button.disabled = True
            self.left_button.disabled = True
        elif self.page == self.length - 1:
            self.right_button.disabled = True
            self.last_button.disabled = True

    @property
    def page_button_label(self) -> str:
        return f"{self.page + 1}/{self.length}"

    def switch_container(self, page: int) -> PaginatedLayoutView:
        self.view.clear_items()
        return self.view.add_item(self.view.containers[page])

    @ui.button(label="<<")
    async def first_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(view=self.switch_container(0))

    @ui.button(label="<")
    async def left_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(view=self.switch_container(self.page - 1))

    @ui.button(style=ButtonStyle.blurple, disabled=True)
    async def page_button(self, _: Interaction, __: Button) -> None:
        pass

    @ui.button(label=">")
    async def right_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(view=self.switch_container(self.page + 1))

    @ui.button(label=">>")
    async def last_button(self, interaction: Interaction, _: Button) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(view=self.switch_container(self.length - 1))


class PaginatedLayoutView(LayoutView):
    def __init__(self, *, timeout: float = 180, containers: list[Container] | Container) -> None:
        self.containers = containers if isinstance(containers, list) else [containers]
        self.length: int = len(self.containers)
        if self.length > 1:
            for i, container in enumerate(self.containers):
                container.add_item(ui.Separator()).add_item(PaginateActionRow(i, self.length))
        super().__init__(containers[0], timeout=timeout)
