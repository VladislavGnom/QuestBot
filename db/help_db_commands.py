import secrets
import aiosqlite
from aiogram import Bot
from db.database import get_db_connection

async def add_player_to_team(user_id: int, username: str, team_id: int):
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT OR IGNORE INTO players (user_id, username, team_id) VALUES (?, ?, ?)",
                (user_id, username, team_id)
            )
            await conn.commit()

async def get_team_players(team_id: int):
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT user_id FROM players WHERE team_id = ?", (team_id,))
            players = [row[0] for row in await cursor.fetchall()]
            return players

async def get_exist_teams():
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT id FROM teams")
            teams = [row[0] for row in await cursor.fetchall()]
            return teams

async def update_game_state(team_id: int, player_index: int, status: str):
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                '''INSERT OR REPLACE INTO game_state 
                (team_id, current_player_index, status) 
                VALUES (?, ?, ?)''',
                (team_id, player_index, status)
            )
            await conn.commit()

async def create_team_if_not_exists(team_name: str):
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            # Проверяем существование команды
            await cursor.execute("SELECT id FROM teams WHERE name = ?", (team_name,))
            existing_team = await cursor.fetchone()
            
            if existing_team:
                team_id = existing_team[0]
                created = False
            else:
                # Создаем новую команду
                await cursor.execute("INSERT INTO teams (name) VALUES (?)", (team_name,))
                await conn.commit()
                team_id = cursor.lastrowid
                created = True
            
            return team_id, created

async def get_game_progress(team_id: int):
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM game_progress WHERE team_id = ?", 
                (team_id,)
            )
            progress = await cursor.fetchone()
            return progress

async def update_game_progress(team_id: int, player_id: int, question_num: int, status: str):
    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                '''INSERT OR REPLACE INTO game_progress 
                (team_id, current_player_id, current_question, status) 
                VALUES (?, ?, ?, ?)''',
                (team_id, player_id, question_num, status)
            )
            await conn.commit()

# --------------------------------

async def generate_invite_link(bot: Bot, team_id: int, team_name: str):
    # Генерируем уникальный токен
    token = secrets.token_urlsafe(16)
    async with get_db_connection() as conn:
        await conn.execute(
            "UPDATE teams SET invite_token = ? WHERE id = ?",
            (token, team_id)
        )
        await conn.commit()
    
    # Создаем ссылку вида https://t.me/your_bot?start=join_<team_id>_<token>
    return f"https://t.me/{(await bot.me()).username}?start=join_{team_id}_{token}"

async def create_team(admin_id: int, team_name: str):
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "INSERT INTO teams (name, admin_id) VALUES (?, ?) RETURNING id",
            (team_name, admin_id))
        team_id = (await cursor.fetchone())[0]
        await conn.commit()
    return team_id

ADMIN_IDS = [1636968793]

async def join_team(user_id: int, team_id: int, token: str) -> tuple[bool, str]:
    """
    Пытается добавить пользователя в команду
    Возвращает True если успешно, False если:
    - неверный токен
    - пользователь уже в другой команде
    - пользователь уже в этой команде
    """
    async with get_db_connection() as conn:
        # Проверяем валидность токена
        cursor = await conn.execute(
            "SELECT 1 FROM teams WHERE id = ? AND invite_token = ?",
            (team_id, token)
        )
        valid = await cursor.fetchone()

        if not valid:
            return False, 'Не удалось подсоединиться: ссылка недействительна.'
        
        # Проверяем, не состоит ли уже пользователь в какой-либо команде
        cursor = await conn.execute(
            "SELECT team_id FROM team_members WHERE user_id = ?",
            (user_id,)
        )
        existing_team = await cursor.fetchone()
        
        if existing_team:
            # Пользователь уже в команде
            text = 'Вы уже находитесь в этой команде - {team_name}.' if existing_team[0] == team_id else 'Вы не можете подсоединиться к другой команде, когда уже подключились к предыдущей.'
            return existing_team[0] == team_id, text    # True если это та же команда
            
        # Добавляем пользователя в команду
        await conn.execute(
            "INSERT INTO team_members (user_id, team_id) VALUES (?, ?)",
            (user_id, team_id)
        )
        await conn.commit()
        return True, 'Вы успешно присоединились к команде {team_name}!'
        
async def get_team_name(team_id: int):
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT name FROM teams WHERE id = ?",
            (team_id,)
        )

        row = await cursor.fetchone()
        return row[0] if row else None

async def get_team_members(team_id: int):
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT user_id FROM team_members WHERE team_id = ?",
            (team_id,)
        )
        return [row[0] for row in await cursor.fetchall()]

async def is_admin(user_id: int):
    # Здесь реализуйте проверку, является ли пользователь админом
    # Например, можно хранить список админов в БД или конфиге
    return user_id in ADMIN_IDS  # Замените на вашу логику
