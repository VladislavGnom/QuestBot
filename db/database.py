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
                name TEXT NOT NULL,
                admin_id INTEGER NOT NULL,
                invite_token TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            # Единая таблица игроков (заменяет team_members и players)
            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY, 
                username TEXT, 
                full_name TEXT,
                team_id INTEGER NOT NULL,
                is_captain BOOLEAN DEFAULT FALSE,
                location INTEGER DEFAULT 1,  -- Номер стартовой локации
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
        