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

import os

from dotenv import load_dotenv

load_dotenv()

# Basic
DEFAULT_PREFIX = "!"
ACTIVITY_NAME = "Wordle ▪ /minigame wordle"
TOKEN = os.getenv("BOT_TOKEN", "")
DEBUG_WEBHOOK = os.getenv("DEBUG_WEBHOOK", "")
OWNER_ID = 596886610214125598

# GIF
LOADING_GIF = "https://cdn.discordapp.com/emojis/1187957747724079144.gif?size=64&name=loading&quality=lossless"
PLAYING_GIF = "https://cdn.discordapp.com/emojis/1174925797082017923.gif?size=64&name=playing&quality=lossless"

# Emojis
SKIP_EMOJI = "https://cdn.discordapp.com/emojis/1174966018280529931.png?size=64&name=skip&quality=lossless"

# Emotes
CHECKMARK = "<a:check:1238796460569657375>"
CROSS = "<a:crossout:1358833476979261702>"
LOADING_EMOJI = "<a:loading:1187957747724079144>"
PLAYING_EMOJI = "<a:playing:1174925797082017923>"

# Music Cog
LAVA_URL = os.getenv("LAVA_URL", "localhost")
LAVA_PW = os.getenv("LAVA_PW", "thanhz")
BACKUP_LL = os.getenv("BACKUP_LL")
BACKUP_LL_PW = os.getenv("BACKUP_LL_PW")

# Utils Cog
WORDNIK_API = os.getenv("WORDNIK_API")

# Fun Cog
FORTUNE_KEY = int(os.getenv("FORTUNE_KEY", "1234"))
FORTUNE_YAPPING_KEY = int(os.getenv("FORTUNE_YAPPING_KEY", "9876"))
