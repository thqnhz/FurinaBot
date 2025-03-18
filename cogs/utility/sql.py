# This is a file that will contain all the sql string for easier management

from __future__ import annotations

from typing import List

from asyncpg import Pool, Record
        

class PrefixSQL:
    """Bot prefix related SQL"""
    def __init__(self, *, pool: Pool):
        self.pool=pool

    async def create_prefix_table(self):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_prefixes
                (
                    guild_id BIGINT NOT NULL PRIMARY KEY,
                    prefix TEXT NOT NULL
                )
                """)
        
    async def get_custom_prefixes(self) -> List[Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch("""SELECT * FROM custom_prefixes""")

    async def set_custom_prefix(self, *, guild_id: int, prefix: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                    INSERT INTO custom_prefixes (guild_id, prefix)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO UPDATE SET
                    prefix = excluded.prefix
                """, guild_id, prefix
            )

    async def delete_custom_prefix(self, *, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute("""DELETE FROM custom_prefixes WHERE guild_id = $1""", guild_id)


class MinigamesSQL:
    def __init__(self, *, pool: Pool):
        self.pool = pool
        
    async def init_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                    CREATE TABLE IF NOT EXISTS singleplayer_games
                    (
                        game_id BIGINT NOT NULL PRIMARY KEY,
                        game_name TEXT NOT NULL,
                        user_id BIGINT NOT NULL,
                        attempts INT NOT NULL,
                        win BOOLEAN DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS twoplayers_games
                    (
                        game_id BIGINT NOT NULL PRIMARY KEY,
                        game_name TEXT NOT NULL,
                        user1_id BIGINT NOT NULL,
                        user2_id BIGINT,
                        attempts INT NOT NULL,
                        win BIGINT
                    )
                """)

    async def update_game_status(self, *, game_id: int, game_name: str, user_id: int, attempts: int, win: bool):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                    INSERT INTO singleplayer_games (game_id, game_name, user_id, attempts, win)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (game_id) DO UPDATE SET
                    attempts = EXCLUDED.attempts,
                    win = EXCLUDED.win
                """, game_id, game_name, user_id, attempts, win
            )

    async def get_minigame_stats_all(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                WITH ranked_players AS (
                    SELECT 
                        game_name,
                        user_id,
                        COUNT(*) FILTER (WHERE win = TRUE) AS wins,
                        ROW_NUMBER() OVER (PARTITION BY game_name ORDER BY COUNT(*) FILTER (WHERE win = TRUE) DESC) AS rank
                    FROM 
                        singleplayer_games
                    GROUP BY 
                        game_name, user_id
                )
                SELECT 
                    game_name,
                    user_id,
                    wins
                FROM 
                    ranked_players
                WHERE 
                    rank <= 3
                ORDER BY 
                    game_name, rank;
            """)
        
    async def get_minigame_stats_user(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT 
                    game_name,
                    COUNT(*) FILTER (WHERE win = TRUE) AS wins,
                    COUNT(*) FILTER (WHERE win = FALSE) AS losses,
                    COUNT(*) AS total_games
                FROM 
                    singleplayer_games
                WHERE 
                    user_id = $1
                GROUP BY 
                    game_name
                ORDER BY 
                    game_name;
            """, user_id)

    async def get_top_players_by_minigame(self, minigame: str):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT 
                    user_id,
                    COUNT(*) FILTER (WHERE win = TRUE) AS wins,
                    COUNT(*) FILTER (WHERE win = FALSE) AS losses,
                    COUNT(*) AS total_games,
                    ROUND((COUNT(*) FILTER (WHERE win = TRUE) * 100.0 / NULLIF(COUNT(*), 0)), 2) AS win_percentage
                FROM 
                    singleplayer_games
                WHERE 
                    game_name = $1
                GROUP BY 
                    user_id
                HAVING 
                    COUNT(*) >= 5
                ORDER BY 
                    win_percentage DESC,
                    total_games DESC
                LIMIT 3
            """, minigame)

    async def get_bottom_players_by_minigame(self, minigame: str):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT 
                    user_id,
                    COUNT(*) FILTER (WHERE win = TRUE) AS wins,
                    COUNT(*) FILTER (WHERE win = FALSE) AS losses,
                    COUNT(*) AS total_games,
                    ROUND((COUNT(*) FILTER (WHERE win = TRUE) * 100.0 / NULLIF(COUNT(*), 0)), 2) AS win_percentage
                FROM 
                    singleplayer_games
                WHERE 
                    game_name = $1
                GROUP BY 
                    user_id
                HAVING 
                    COUNT(*) >= 5
                ORDER BY 
                    win_percentage ASC,  
                    total_games DESC 
                LIMIT 3
            """, minigame)

