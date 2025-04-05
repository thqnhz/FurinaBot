from __future__ import annotations

from typing import TYPE_CHECKING

import discord
import logging
from aiohttp import ClientSession
from asyncpg import Pool
from discord import Embed
from discord.ext.commands import Context, Cog

from settings import CHECKMARK


if TYPE_CHECKING:
    from furina import FurinaBot
    


