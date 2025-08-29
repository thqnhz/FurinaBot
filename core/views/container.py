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

from typing import Self

from discord import ui


class Container(ui.Container):
    """A subclass from :class:`discord.ui.Container` that has some qol methods"""

    def __init__(self, *children: ui.Item) -> None:
        super().__init__(*children)

    def add_items(self, *items: ui.Item) -> Self:
        """Add multiple items to the container"""
        for item in items:
            self.add_item(item)
        return self
