from discord import Color
from discord.ext import commands

from bot import Furina
from keep_alive import keep_alive
from settings import TOKEN
from _classes.embeds import FooterEmbed

bot = Furina()

@bot.hybrid_command(name="sync", hidden=True, description="Sync app commands.")
@commands.is_owner()
async def sync(ctx: commands.Context) -> None:
    synced = await bot.tree.sync()
    embed = FooterEmbed(
        title=f"Synced {len(synced)} slash commands.",
        description="\n".join(f"</{cmd.name}:{cmd.id}>" for cmd in synced),
        color=Color.blue()
    )
    await ctx.reply(embed=embed)

keep_alive()
bot.run(TOKEN)

