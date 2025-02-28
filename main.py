from __future__ import annotations

import asyncio
import os
import logging

import asqlite
from aiohttp import ClientSession


from bot import FurinaBot
from settings import TOKEN
       

class LogFormatter(logging.Formatter):
    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self):
        super().__init__()
        self.FORMATS = {
            logging.DEBUG:    self.grey     + "%(asctime)s | %(levelname)8s" + self.reset + " | %(message)s",
            logging.INFO:     self.blue     + "%(asctime)s | %(levelname)8s" + self.reset + " | %(message)s",
            logging.WARNING:  self.yellow   + "%(asctime)s | %(levelname)8s" + self.reset + " | %(message)s",
            logging.ERROR:    self.red      + "%(asctime)s | %(levelname)8s" + self.reset + " | %(message)s",
            logging.CRITICAL: self.bold_red + "%(asctime)s | %(levelname)8s" + self.reset + " | %(message)s"
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def handle_setup_logging() -> None:
    """Setup logging for the bot"""
    from discord import utils
    timestamp = utils.utcnow().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/furina_{timestamp}.log"

    file_handler = logging.FileHandler(log_filename)
    console_handler = logging.StreamHandler()
    file_handler.setFormatter(LogFormatter())
    console_handler.setFormatter(LogFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # utils.setup_logging()
    
def delete_old_logs() -> None:
    """Delete old logs"""
    logs = sorted([file for file in os.listdir("logs") if file.startswith("furina_") and file.endswith(".log")])
    if len(logs) > 2:
        for log in logs[:-2]:
            os.remove(f"logs/{log}")

async def main() -> None:
    os.makedirs("logs", exist_ok=True)
    delete_old_logs()
    handle_setup_logging()
    async with ClientSession() as client_session, asqlite.create_pool("config.db") as pool:
        async with FurinaBot(pool=pool, client_session=client_session) as bot:
            await bot.start(TOKEN)

asyncio.run(main())
