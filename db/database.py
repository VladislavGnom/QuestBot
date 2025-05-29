import aiosqlite
from datetime import datetime
from contextlib import asynccontextmanager

async def init_db():
    async with aiosqlite.connect('quest_bot.db') as conn:
        async with conn.cursor() as cursor:
            # Таблица команд
            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Таблица игроков
            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                team_id INTEGER,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
            ''')
            
            # Таблица состояния игры
            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_state (
                team_id INTEGER PRIMARY KEY,
                current_player_index INTEGER DEFAULT 0,
                status TEXT DEFAULT 'waiting',
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
            ''')

            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_progress (
                team_id INTEGER PRIMARY KEY,
                current_player_id INTEGER,
                current_question INTEGER,
                status TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
            ''')
            
            await conn.commit()

@asynccontextmanager
async def get_db_connection():
    conn = await aiosqlite.connect('quest_bot.db')
    try:
        yield conn
    finally:
        await conn.close()
        