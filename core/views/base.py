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

from discord import Interaction, Member, Message, User, ui
from discord.ext.commands import CooldownMapping

from .errors import UIElementOnCoolDownError

if TYPE_CHECKING:
    from .container import Container


class View(ui.View):
    """A View that auto disable children when timed out"""

    def __init__(self, *, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.message: Message
        self.cd = CooldownMapping.from_cooldown(rate=1, per=2, type=self.key)

    @staticmethod
    def key(interaction: Interaction) -> User | Member:
        return interaction.user

    async def interaction_check(self, interaction: Interaction) -> bool:
        retry_after = self.cd.update_rate_limit(interaction)
        if retry_after:
            raise UIElementOnCoolDownError(retry_after=retry_after)
        return True

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item
    ) -> None:
        if isinstance(error, UIElementOnCoolDownError):
            seconds = str(error.retry_after)[:3]
            await interaction.response.send_message(
                f"You are clicking too fast, try again in {seconds} seconds!",
                ephemeral=True,
            )
        else:
            await super().on_error(interaction, error, item)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, ui.Button) and child.url:
                continue
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except AttributeError:
            pass


class LayoutView(ui.LayoutView):
    """
    A `ui.LayoutView`
    that auto disable its children when timed out
    and has per user rate limit
    """

    def __init__(self, container: Container, *, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.add_item(container)
        self.cd = CooldownMapping.from_cooldown(rate=1, per=1, type=self.key)
        self.message: Message

    @staticmethod
    def key(interaction: Interaction) -> User | Member:
        return interaction.user

    async def interaction_check(self, interaction: Interaction) -> bool:
        retry_after = self.cd.update_rate_limit(interaction)
        if retry_after:
            raise UIElementOnCoolDownError(retry_after=retry_after)
        return True

    async def on_error(
        self, interaction: Interaction, error: Exception, item: ui.Item
    ) -> None:
        if isinstance(error, UIElementOnCoolDownError):
            await interaction.response.send_message(
                "Slow down! You are clicking too fast!", ephemeral=True
            )
        else:
            await super().on_error(interaction, error, item)

    async def on_timeout(self) -> None:
        for child in self.walk_children():
            if isinstance(child, ui.Button) and child.url:
                continue
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except AttributeError:
            pass
