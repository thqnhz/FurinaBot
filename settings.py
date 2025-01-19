import os
from dotenv import load_dotenv

load_dotenv()

# Basic
DEFAULT_PREFIX = "!"
ACTIVITY_NAME = "Music » /play"
TOKEN = os.getenv("BOT_TOKEN2")
DEBUG_WEBHOOK = os.getenv("DEBUG_WEBHOOK")

# GIF
LOADING_GIF = "https://cdn.discordapp.com/emojis/1187957747724079144.gif?size=64&name=loading&quality=lossless"
PLAYING_GIF = "https://cdn.discordapp.com/emojis/1174925797082017923.gif?size=64&name=playing&quality=lossless"

# Emojis
SKIP_EMOJI = "https://cdn.discordapp.com/emojis/1174966018280529931.png?size=64&name=skip&quality=lossless"

# Emotes
CHECKMARK = "<a:check:1238796460569657375>"

# Music Cog
MUSIC_CHANNEL = 1089851760425848923
MUSIC_WEBHOOK = os.getenv("MUSIC_WEBHOOK")
LAVA_URI = os.getenv("LAVA_URI")
LAVA_BACKUP = os.getenv("LAVA_BACKUP")
LAVA_PW = os.getenv("LAVA_PW")

# Hidden Cog
instance_name = "furina"

# Edit this if you are using different package manager, I'm using PM2
REBOOT_CMD = f"pm2 start {instance_name}"

# Edit this if your logs file location is different, since I'm using pm2 and host the bot on AWS
# the logs file is at /home/ubuntu/.pm2/logs/{instance_name}-error.log
LOG_FILE = f"/home/ubuntu/.pm2/logs/{instance_name}-error.log"


