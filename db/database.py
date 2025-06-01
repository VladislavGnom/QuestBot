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
                team_id INTEGER,
                is_captain BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                location INTEGER DEFAULT 1,  -- Номер стартовой локации
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
            ''')

            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_game_states (
                team_id INTEGER PRIMARY KEY,
                current_player_idx INTEGER DEFAULT 0,
                players_order TEXT,  -- JSON массив [user_id1, user_id2, ...]
                current_question_num INTEGER DEFAULT 1,
                current_question_idx INTEGER DEFAULT 0,
                deadline TEXT,       -- TIMESTAMP
                correct_answers INTEGER DEFAULT 0,
                status TEXT DEFAULT 'waiting',  -- waiting/playing/finished
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
            ''')

            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS state_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                state_data TEXT NOT NULL,  -- JSON с состоянием
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT DEFAULT (datetime('now', '+1 hour')),
                FOREIGN KEY (sender_id) REFERENCES players(user_id),
                FOREIGN KEY (receiver_id) REFERENCES players(user_id)
            )
            ''')

            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,               -- Название локации
                description TEXT,                 -- Описание для игроков
                coordinates TEXT,                 -- "lat,lon" или "x,y,z"
                image_path TEXT,                  -- Путь к изображению
                is_hidden BOOLEAN DEFAULT FALSE,  -- Скрыта ли локация
                unlock_condition TEXT             -- Условие разблокировки
            )
            ''')

            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id INTEGER NOT NULL,     -- К какой локации привязан
                question_text TEXT NOT NULL,      -- Текст вопроса
                answer TEXT NOT NULL,             -- Правильный ответ
                answer_hint TEXT,                 -- Подсказка
                difficulty INTEGER DEFAULT 1,     -- Сложность (1-5)
                question_type TEXT DEFAULT 'text',-- text/photo/video/audio
                media_path TEXT,                  -- Путь к медиафайлу
                cost INTEGER DEFAULT 10,          -- Баллы за правильный ответ
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
            ''')

            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                start_location_id INTEGER,
                is_active BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (start_location_id) REFERENCES locations(id)
            )
            ''')

            await cursor.execute('''
            CREATE TABLE IF NOT EXISTS quest_locations (
                quest_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                order_num INTEGER,                -- Порядковый номер в квесте
                PRIMARY KEY (quest_id, location_id),
                FOREIGN KEY (quest_id) REFERENCES quests(id),
                FOREIGN KEY (location_id) REFERENCES locations(id)
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
        