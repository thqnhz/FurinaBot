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

__all__ = [
    "LayoutView",
    "PaginatedView",
    "View",
]

from typing import Literal

from discord import Button, ButtonStyle, Embed, Interaction, Message, User, ui
from discord.ext.commands import CommandError, CooldownMapping


class UIElementOnCoolDownError(CommandError):
    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after


class View(ui.View):
    """A View that auto disable children when timed out"""
    def __init__(self, *, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.message: Message
        self.cd = CooldownMapping.from_cooldown(rate=1, per=2, type=self.key)

    @staticmethod
    def key(interaction: Interaction) -> User:
        return interaction.user

    async def interaction_check(self, interaction: Interaction) -> Literal[True]:
        retry_after = self.cd.update_rate_limit(interaction)
        if retry_after:
            raise UIElementOnCoolDownError(retry_after=retry_after)
        return True

    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Item) -> None:
        if isinstance(error, UIElementOnCoolDownError):
            seconds = int(error.retry_after)
            unit = 'second' if seconds == 1 else 'seconds'
            await interaction.response.send_message(
                f"You are clicking too fast, try again in {seconds} {unit}!", ephemeral=True
            )
        else:
            await super().on_error(interaction, error, item)

    async def on_timeout(self) -> None:
        if hasattr(self, 'message'):
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)


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
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @ui.button(label="<", disabled=True)
    async def left_button(self, interaction: Interaction, _: Button) -> None:
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @ui.button(style=ButtonStyle.blurple, disabled=True)
    async def page_button(self, _: Interaction, __: Button) -> None:
        pass

    @ui.button(label=">")
    async def right_button(self, interaction: Interaction, _: Button) -> None:
        self.page += 1 if self.page <= self.length - 1 else self.page
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @ui.button(label=">>")
    async def last_button(self, interaction: Interaction, _: Button) -> None:
        self.page = self.length - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)


class LayoutView(ui.LayoutView):
    """
    A :class:`discord.ui.LayoutView` that auto disable its children when timed out
    and has per user rate limit
    """
    def __init__(self, *, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.cd = CooldownMapping.from_cooldown(rate=1, per=1, type=self.key)

    @staticmethod
    def key(interaction: Interaction) -> User:
        return interaction.user

    async def interaction_check(self, interaction: Interaction) -> Literal[True]:
        retry_after = self.cd.update_rate_limit(interaction)
        if retry_after:
            raise UIElementOnCoolDownError(retry_after=retry_after)
        return True

    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Item) -> None:
        if isinstance(error, UIElementOnCoolDownError):
            await interaction.response.send_message(
                "Slow down! You are clicking too fast!", ephemeral=True
            )
        else:
            await super().on_error(interaction, error, item)

    async def on_timeout(self) -> None:
        if hasattr(self, 'message'):
            for child in self.walk_children():
                child.disabled = True
            await self.message.edit(view=self)


