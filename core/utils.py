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

from __future__ import annotations

import logging
import logging.handlers
import pathlib


class LogFormatter(logging.Formatter):
    """Custom log formatter for the bot"""
    GREY = '\x1b[38;21m'
    BLUE = '\x1b[38;5;39m'
    YELLOW = '\x1b[38;5;226m'
    RED = '\x1b[38;5;196m'
    BOLD_RED = '\x1b[31;1m'
    RESET = '\x1b[0m'

    def __init__(self) -> None:
        super().__init__()
        self.FORMATS = {
            logging.DEBUG:    self.GREY     + "%(asctime)s | %(levelname)8s" + self.RESET + " | %(name)20s : %(message)s",  # noqa: E221, E501
            logging.WARNING:  self.YELLOW   + "%(asctime)s | %(levelname)8s" + self.RESET + " | %(name)20s : %(message)s",  # noqa: E221, E501
            logging.ERROR:    self.RED      + "%(asctime)s | %(levelname)8s" + self.RESET + " | %(name)20s : %(message)s",  # noqa: E221, E501
            logging.INFO:     self.BLUE     + "%(asctime)s | %(levelname)8s" + self.RESET + " | %(name)20s : %(message)s",  # noqa: E221, E501
            logging.CRITICAL: self.BOLD_RED + "%(asctime)s | %(levelname)8s" + self.RESET + " | %(name)20s : %(message)s",  # noqa: E501
        }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging() -> None:
    """Setup logging for the bot

    The bot will use both file logging and console logging.
    Default directory of log file is `logs/furina.log`
    
    Colors
    ------
    - DEBUG = grey
    - WARNING = yellow
    - ERROR = red
    - INFO = blue
    - CRITICAL = bold_red

    Format
    ------
    `%(asctime)s | %(levelname)8s | %(name)20s : %(message)s`
    """
    LOG_DIR = pathlib.Path() / 'logs'
    LOG_DIR.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_DIR / 'furina.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32MB
        backupCount=3
    )
    file_handler.setFormatter(LogFormatter())
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LogFormatter())
    root_logger.addHandler(console_handler)
