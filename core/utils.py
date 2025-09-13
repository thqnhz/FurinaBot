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
import re
from typing import TYPE_CHECKING, Any

from discord import Embed, ui

# since multiple utils will be confusing so just import everything from discord.utils
from discord.utils import *  # type: ignore[wildcardImportFromLibrary]

from core.views import Container, PaginatedLayoutView

if TYPE_CHECKING:
    from aiohttp import ClientSession


URL_REGEX = re.compile(r"https?://(?:www\.)?.+")


class LogFormatter(logging.Formatter):
    """Custom log formatter for the bot"""

    GREY = "\x1b[38;21m"
    BLUE = "\x1b[38;5;39m"
    YELLOW = "\x1b[38;5;226m"
    RED = "\x1b[38;5;196m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    def __init__(self) -> None:
        super().__init__()
        self.FORMATS = {
            logging.DEBUG: self.GREY
            + "%(asctime)s | %(levelname)8s"
            + self.RESET
            + " | %(name)20s : %(message)s",
            logging.WARNING: self.YELLOW
            + "%(asctime)s | %(levelname)8s"
            + self.RESET
            + " | %(name)20s : %(message)s",
            logging.ERROR: self.RED
            + "%(asctime)s | %(levelname)8s"
            + self.RESET
            + " | %(name)20s : %(message)s",
            logging.INFO: self.BLUE
            + "%(asctime)s | %(levelname)8s"
            + self.RESET
            + " | %(name)20s : %(message)s",
            logging.CRITICAL: self.BOLD_RED
            + "%(asctime)s | %(levelname)8s"
            + self.RESET
            + " | %(name)20s : %(message)s",
        }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging() -> None:
    """Setup logging for the bot

    The bot will use both file logging and console logging.
    Default directory of log file is `logs/furina.log`.

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
    LOG_DIR = pathlib.Path() / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_DIR / "furina.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32MB
        backupCount=3,
    )
    file_handler.setFormatter(LogFormatter())
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LogFormatter())
    root_logger.addHandler(console_handler)


# Dictionary related
async def call_dictionary(word: str, cs: ClientSession) -> PaginatedLayoutView:
    """|coro|

    Make a http request to dictionaryapi.dev to get definition of a word.
    If the word has no definition or has a single definition, returns a single embed.
    *(already processed inside :class:`~core.views.PaginatedView`)*

    Parameters
    ----------
    word : :class:`str`
        The word to get the definition.
    cs : :class:`aiohttp.ClientSession`
        Client session to make request.

    Returns
    -------
    :class:`~core.views.PaginatedLayoutView`
        The paginated view with embeds of the word's definitions.
    """
    containers: list[Container] = []
    dictionary_link = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    async with cs.get(dictionary_link) as response:
        if response.status == 404:
            return PaginatedLayoutView(
                containers=Container(
                    ui.TextDisplay(
                        f"## {word.capitalize}\nNo definitions found. API call returned 404."
                    )
                )
            )
        data: list[dict] = await response.json()

    pronunciations = __get_pronunciations(data)

    for i, d in enumerate(data):
        # Definitions
        meanings: list[dict] = d.get("meanings", [])
        for meaning in meanings:
            conjugation: str = meaning.get("partOfSpeech", "N/A")
            synonyms: list[str] = meaning.get("synonyms")
            synonyms_txt = ", ".join(synonyms) if synonyms else "N/A"
            antonyms: list[str] = meaning.get("antonyms")
            antonyms_txt = ", ".join(antonyms) if antonyms else "N/A"
            definitions: list[dict] = meaning.get("definitions")  # type: ignore[reportAssignmentType]
            definition_value = ""
            FIELD_LIMIT: int = 1024
            for definition in definitions:
                definition_text: str = definition.get("definition")  # type: ignore[reportAssignmentType]
                to_add: str = f"\n- {definition_text}"
                example: str = definition.get("example", "")
                if example:
                    to_add += f"\n  - Ex: *{example}*"
                if len(definition_value) + len(to_add) < FIELD_LIMIT:
                    definition_value += to_add
                else:
                    break

            container = Container(
                ui.TextDisplay(
                    f"## {word.capitalize()} ({conjugation})\n"
                    f"### Pronunciations:\n{pronunciations[i] or 'N/A'}\n"
                    f"### Synonyms:\n{synonyms_txt}\n"
                    f"### Antonyms:\n{antonyms_txt}\n"
                    f"### Definition:\n{definition_value}"
                )
            )
            containers.append(container)
    return PaginatedLayoutView(timeout=300, containers=containers)


def __get_pronunciations(data: list[dict]) -> list[str]:
    """Get the word's pronunciations

    Parameters
    ----------
    data : :class:`dict`
        The returned data from the API call.

    Returns
    -------
    :class:`list[str]`
        The word's pronunciations.
        If no pronunciations found for that definition, the string at that index will be empty.
    """
    result: list[str] = [""] * len(data)
    for i, d in enumerate(data):
        phonetics: str | None = d.get("phonetic")
        if not phonetics:
            phonetics_list: list[dict] = d.get("phonetics", [])
            phonetics = ", ".join(
                [phone.get("text") for phone in phonetics_list if phone.get("text")]  # type: ignore[reportIndexIssue]
            )
            if phonetics:
                result[i] = f"`{phonetics}`"
        else:
            result[i] = f"`{phonetics}`"
    return result
