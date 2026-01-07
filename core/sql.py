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

import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    import asqlite

# Base
GUILDS_SQL = """
    CREATE TABLE IF NOT EXISTS guilds
    (
        id INTEGER NOT NULL PRIMARY KEY
    )
"""
USERS_SQL = """
    CREATE TABLE IF NOT EXISTS users
    (
        id INTEGER NOT NULL PRIMARY KEY
    )
"""
# Events Cog
PREFIX_COMMANDS_SQL = """
    CREATE TABLE IF NOT EXISTS prefix_commands
    (
        guild_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        command TEXT NOT NULL,
        FOREIGN KEY (guild_id) REFERENCES guilds (id),
        FOREIGN KEY (author_id) REFERENCES users (id)
    )
"""
APP_COMMANDS_SQL = """
    CREATE TABLE IF NOT EXISTS app_commands
    (
        guild_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        command TEXT NOT NULL,
        FOREIGN KEY (guild_id) REFERENCES guilds (id),
        FOREIGN KEY (author_id) REFERENCES users (id)
    )
"""
# Gacha Cog
GI_UID_SQL = """
    CREATE TABLE IF NOT EXISTS gi_uid
    (
        user_id INTEGER NOT NULL PRIMARY KEY,
        uid TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
"""
HSR_UID_SQL = """
    CREATE TABLE IF NOT EXISTS hsr_uid
    (
        user_id INTEGER NOT NULL PRIMARY KEY,
        uid TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
"""
# Minigames Cog
SINGLEPLAYER_GAMES_SQL = """
    CREATE TABLE IF NOT EXISTS singleplayer_games
    (
        game_id INTEGER NOT NULL PRIMARY KEY,
        game_name TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        attempts INT NOT NULL,
        win BOOLEAN DEFAULT NULL
    )
"""
TWOPLAYER_GAMES_SQL = """
    CREATE TABLE IF NOT EXISTS twoplayers_games
    (
        game_id INTEGER NOT NULL PRIMARY KEY,
        game_name TEXT NOT NULL,
        user1_id INTEGER NOT NULL,
        user2_id INTEGER,
        attempts INT NOT NULL,
        win BOOLEAN DEFAULT NULL
    )
"""
# Utils Cog
CUSTOM_PREFIX_SQL = """
    CREATE TABLE IF NOT EXISTS custom_prefixes
    (
        guild_id INTEGER NOT NULL PRIMARY KEY,
        prefix TEXT NOT NULL,
        FOREIGN KEY (guild_id) REFERENCES guilds (id)
    )
"""

# Music Cog
MUSIC_CHANNEL = """
    CREATE TABLE IF NOT EXISTS music_channel
    (
        guild_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL PRIMARY KEY,
        FOREIGN KEY (guild_id) REFERENCES guilds (id)
    )
"""

# Tags Cog
TAGS_SQL = """
    CREATE TABLE IF NOT EXISTS tags
    (
        guild_id INTEGER NOT NULL,
        owner INTEGER NOT NULL,
        name TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        uses INTEGER DEFAULT 0,
        PRIMARY KEY (guild_id, owner, name)
    )
"""
TAG_ALIASES_SQL = """
    CREATE TABLE IF NOT EXISTS tag_aliases -- for tag aliases and look up table
    (
        guild_id INTEGER NOT NULL,
        owner INTEGER NOT NULL, -- owner of the alias, not the tag owner
        name TEXT NOT NULL, -- original tag name
        alias TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        uses INTEGER DEFAULT 0,
        PRIMARY KEY (guild_id, name, alias),
        FOREIGN KEY (guild_id, owner, name)
        REFERENCES tags (guild_id, owner, name)
        ON DELETE CASCADE
    )
"""


class SQL:
    """A wrapper to a wrapper of asqlite"""

    def __init__(self, pool: asqlite.Pool) -> None:
        self.pool = pool
        self.create_table_queries = [
            GUILDS_SQL,
            USERS_SQL,
            CUSTOM_PREFIX_SQL,
            PREFIX_COMMANDS_SQL,
            APP_COMMANDS_SQL,
            GI_UID_SQL,
            HSR_UID_SQL,
            SINGLEPLAYER_GAMES_SQL,
            TWOPLAYER_GAMES_SQL,
            MUSIC_CHANNEL,
        ]

    async def create_tables(self) -> None:
        async with self.pool.acquire() as conn, conn.transaction():
            for query in self.create_table_queries:
                await conn.execute(query)

    async def execute(self, query: str, *args: typing.Any) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)

    async def executemany(self, query: str, *args: typing.Any) -> None:
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.executemany(query, *args)

    async def fetchall(
        self, query: str, *args: typing.Any
    ) -> list[sqlite3.Row]:
        async with self.pool.acquire() as conn:
            return await conn.fetchall(query, *args)

    async def fetchone(self, query: str, *args: typing.Any) -> sqlite3.Row:
        async with self.pool.acquire() as conn:
            return await conn.fetchone(query, *args)

    async def fetchval(
        self, query: str, *args: typing.Any
    ) -> typing.Any | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchone(query, *args)
            return None if not row else row[0]


class TagSQL(SQL):
    """A wrapper to a wrapper of asqlite for tags"""

    def __init__(self, pool: asqlite.Pool) -> None:
        self.pool = pool
        self.create_table_queries = [TAGS_SQL, TAG_ALIASES_SQL]
