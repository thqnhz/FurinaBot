import os
import asyncio
import wavelink
import textwrap
import random
import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure
from discord import Color, Activity, ActivityType

from _classes.embeds import *
from _classes.views import *
from _classes.buttons import *
from settings import *


# Music Cog
async def update_activity(bot: commands.Bot, state: str = "N̸o̸t̸h̸i̸n̸g̸"):
    await bot.change_presence(activity=Activity(type=ActivityType.playing,
                                                name=ACTIVITY_NAME,
                                                state=f"Playing: {state}"))


def length_convert(track: wavelink.Playable):
    """
    Chuyển đổi từ milisecond sang phút:giây.
    """
    track_len = '{:02}:{:02}'.format(*divmod(track.length // 1000, 60))
    return track_len


def get_track_list(tracks: list | None) -> str:
    if not tracks:
        return "`không có kết quả nào`"
    else:
        track_list = ""
        for i, track in enumerate(tracks, 1):
            track_name = textwrap.shorten(track.title, width=50, break_long_words=False, placeholder="...")
            track_list += f"\n{i}. **[{track_name}]({track.uri})**\t({length_convert(track)})"
        return track_list


async def update_player_embed(embed: discord.Embed,
                              msg: discord.Message,
                              channel,
                              view: discord.ui.View = None) -> None:
    if view is None:
        try:
            await msg.edit(embed=embed, view=view)
        except Exception as e:
            await channel.send(embed=embed)
            print(e)
    else:
        try:
            view.message = await msg.edit(embed=embed, view=view)
        except Exception as e:
            view.message = await channel.send(embed=embed, view=view)
            print(e)


# Fun Cog
def random_lag_emote() -> str:
    emote = random.choice([
        'https://cdn.7tv.app/emote/60ae9173f39a7552b68f9730/4x.gif',
        'https://cdn.7tv.app/emote/63c9080bec685e58d1727476/4x.gif',
        'https://cdn.7tv.app/emote/60afcde452a13d1adba73d29/4x.gif',
        'https://cdn.7tv.app/emote/62fd78283b5817bb65704cb6/4x.gif',
        'https://cdn.7tv.app/emote/616ecf20ffc7244d797c6ef8/4x.gif',
        'https://cdn.7tv.app/emote/6121af3d5277086f91cd6f03/4x.gif',
        'https://cdn.7tv.app/emote/61ab007b15b3ff4a5bb954f4/4x.gif',
        'https://cdn.7tv.app/emote/64139e886b843cb8a7001681/4x.gif',
        'https://cdn.7tv.app/emote/64dacca4bd944cda3ad5971f/4x.gif',
        'https://cdn.7tv.app/emote/62ff9b877de1b22af65895d7/4x.webp',
        'https://cdn.7tv.app/emote/646748346989b9b0d46adc50/4x.webp'
    ])
    return emote

