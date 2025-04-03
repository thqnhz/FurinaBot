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
                        win BOOLEAN
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
        

class TagSQL:
    def __init__(self, *, pool: Pool):
        self.pool = pool

    async def create_tag_table(self):
        await self.pool.execute(
        """
            CREATE TABLE IF NOT EXISTS tags
                (
                    guild_id BIGINT NOT NULL,
                    owner BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    PRIMARY KEY (guild_id, owner, name)
                )
        """
        )

    async def get_tag(self, *, guild_id: int, name: str) -> str:
        return await self.pool.fetchval("""SELECT content FROM tags WHERE guild_id = $1 AND name = $2""", 
                                        guild_id, name)
        
    async def create_tag(self, *, guild_id: int, owner: int, name: str, content: str):
        await self.pool.execute("""
            INSERT INTO tags (guild_id, owner, name, content)
            VALUES ($1, $2, $3, $4)
            """, guild_id, owner, name, content)

    async def force_delete_tag(self, *, guild_id: int, name: str) -> str:
        deleted = await self.pool.fetchrow("""
            DELETE FROM tags
            WHERE guild_id = $1 AND name = $2
            RETURNING *
            """, guild_id, name)
        if deleted is None:
            return f"Tag `{name}` not found!"
        return f"Deleted tag `{name}`!"
         
    async def delete_tag(self, *, guild_id: int, owner: int, name: str) -> str:
        tag_owner: int = await self.pool.fetchval("""
            SELECT owner FROM tags
            WHERE guild_id = $1 AND name = $2
            """, guild_id, name)
        if tag_owner != owner:
            return "You do not own this tag!"
        await self.pool.execute("""
            DELETE FROM tags
            WHERE guild_id = $1 AND owner = $2 and name = $3
            """, guild_id, owner, name)
        return f"Deleted tag `{name}`!"



