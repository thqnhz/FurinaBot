import aiohttp, asqlite, asyncio, discord, subprocess
from discord import Color
from discord.ext import commands
from typing import cast

from bot import Furina
from settings import TOKEN
from _classes.embeds import FooterEmbed

from keep_alive import keep_alive

async def main():
    discord.utils.setup_logging()

    async with aiohttp.ClientSession() as client_session, asqlite.create_pool("config.db") as pool:
        async with Furina(pool=pool, client_session=client_session) as bot:
            bot.add_command(sync)
            keep_alive()
            await bot.start(TOKEN)

@commands.command(name="sync", hidden=True, description="Sync app commands.")
@commands.is_owner()
async def sync(ctx: commands.Context) -> None:
    bot = cast(Furina, ctx.bot) # this is kinda unnecessary, but for botvar sake we need to cast ctx.bot to Furina type
    synced = await bot.tree.sync()
    embed = FooterEmbed(
        title=f"Synced {len(synced)} slash commands.",
        description="\n".join(f"</{cmd.name}:{cmd.id}>" for cmd in synced),
        color=Color.blue()
    )
    await ctx.reply(embed=embed)

asyncio.run(main())
