from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands, Interaction, Message
from discord.ext import commands



if TYPE_CHECKING:
    from furina import FurinaBot


class Tags(commands.Cog):
    pass



async def setup(bot: FurinaBot):
    await bot.add_cog(Tags(bot))