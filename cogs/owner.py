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

import platform
from typing import TYPE_CHECKING

import psutil
from discord.ext import commands

from core import FurinaCog, FurinaCtx

if TYPE_CHECKING:
    from core import FurinaBot


class Owner(FurinaCog):
    """Owner only commands"""

    @commands.command(name="vps", hidden=True)
    @commands.is_owner()
    async def vps_command(self, ctx: FurinaCtx) -> None:
        """Get VPS Info"""
        # OS Version
        os_version = platform.platform()

        # CPU Usage
        cpu_percent = psutil.cpu_percent()

        # RAM Usage
        memory_info = psutil.virtual_memory()
        ram_total = round(memory_info.total / (1024**3), 2)
        ram_used = round(memory_info.used / (1024**3), 2)
        ram_available = round(memory_info.available / (1024**3), 2)
        ram_cached = round(ram_total - ram_used - ram_available, 2)

        # Disk Usage
        disk_info = psutil.disk_usage("./")
        disk_total = round(disk_info.total / (1024**3), 2)
        disk_used = round(disk_info.used / (1024**3), 2)
        disk_available = round(disk_info.free / (1024**3), 2)

        embed = self.embed
        embed.title = "VPS Info"
        embed.add_field(name="Operating System", value=os_version)
        embed.add_field(name="CPU Usage", value=f"{cpu_percent}%", inline=False)
        embed.add_field(
            name="RAM Usage",
            value=(
                f"- Total: {ram_total}GB\n"
                f"- Used: {ram_used}GB\n"
                f"- Cache: {ram_cached}GB\n"
                f"- Free: {ram_available}GB"
            ),
            inline=False,
        )
        embed.add_field(
            name="Disk Usage",
            value=(
                f"- Total: {disk_total}GB\n"
                f"- Used: {disk_used}GB\n"
                f"- Free: {disk_available}GB"
            ),
            inline=False,
        )
        await ctx.reply(embed=embed)


async def setup(bot: FurinaBot) -> None:
    await bot.add_cog(Owner(bot))
