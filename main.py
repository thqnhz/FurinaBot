from discord.ext import commands

# Custom subclasses
from bot import Furina
from _classes.embeds import *
from _classes.views import *
from settings import *

bot = Furina()

@bot.hybrid_command(name="sync", hidden=True, description="Update slash command cho server.")
@commands.is_owner()
async def sync(ctx: commands.Context) -> None:
    synced = await bot.tree.sync()
    embed = FooterEmbed(
        title=f"Đã đồng bộ hóa {len(synced)} slash commands.",
        color=Color.blue()
    )
    await ctx.reply(embed=embed)


bot.run(TOKEN)

