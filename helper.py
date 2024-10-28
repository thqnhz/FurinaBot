import random

from _classes.embeds import *
from _classes.views import *
from _classes.buttons import *
from settings import *


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

