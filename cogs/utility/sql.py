from __future__ import annotations

from asyncpg import Pool


class MinigamesSQL:
    def __init__(self, pool: Pool):
        self.pool = pool
        
    async def init_tables(self):
        async with self.pool.acquire() as db:
            await db.execute("""
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
            
    async def get_minigame_stats_all(self):
        async with self.pool.acquire() as con:
            return await con.fetch("""
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
        async with self.pool.acquire() as con:
            return await con.fetch("""
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
        async with self.pool.acquire() as con:
            return await con.fetch("""
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
        async with self.pool.acquire() as con:
            return await con.fetch("""
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

