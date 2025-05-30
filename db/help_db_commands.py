import secrets
import aiosqlite
from aiogram import Bot
from aiogram.types import Message
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

async def join_team(message: Message, team_id: int, token: str) -> bool:
    """
    Добавляет игрока в команду с проверками.
    Возвращает:
    - True: успешное вступление
    - False: неверный токен или уже в команде
    """
    user_id = message.from_user.id
    print(f"Добавляем игрока {user_id} в команду {team_id}")

    async with get_db_connection() as conn:
        # Проверяем валидность токена
        cursor = await conn.execute(
            "SELECT 1 FROM teams WHERE id = ? AND invite_token = ?",
            (team_id, token)
        )
        valid = await cursor.fetchone()

        if not valid:
            print(f"Ошибка при добавлении игрока {user_id} в команду {team_id}: токен недействителен")
            return False
        
        # Проверка, что пользователь еще не в команде
        cursor = await conn.execute(
            "SELECT 1 FROM players WHERE user_id = ?",
            (user_id,)
        )
        existing = await cursor.fetchone()
        
        if existing:
            return False
            
        # Добавляем игрока в команду
        try:
            await conn.execute(
                """INSERT INTO players 
                (user_id, team_id, username, full_name) 
                VALUES (?, ?, ?, ?)""",
                (user_id, team_id, 
                 message.from_user.username,
                 message.from_user.full_name)
            )
            await conn.commit()
            print(f"Успешно добавлен игрок {user_id} в команду {team_id}")
            return True
        except aiosqlite.IntegrityError as error:
            return False
        
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


async def get_team_captain(team_id: int) -> int:
    """Получает ID капитана (админа) команды"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT admin_id FROM teams WHERE id = ?", 
            (team_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None

async def mention_user(user_id: int) -> str:
    """Форматирует упоминание пользователя"""
    username = await get_username(user_id)

    return f"@{username}"  

# async def get_quest_status(team_id: int) -> str:
#     """Проверяет статус квеста команды"""
#     async with get_db_connection() as conn:
#         cursor = await conn.execute(
#             "SELECT status FROM game_progress WHERE team_id = ?",
#             (team_id,)
#         )
#         result = await cursor.fetchone()
#         return result[0] if result else None

async def get_user_team(user_id: int) -> int | None:
    """Возвращает ID команды игрока или None"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT team_id FROM players WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None
    
async def get_team_players(team_id: int) -> list[dict]:
    """Возвращает список игроков команды для квеста"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """SELECT user_id, username, full_name, is_captain, location 
            FROM players 
            WHERE team_id = ? 
            ORDER BY joined_at""",
            (team_id,)
        )
        return [{
            'id': row[0],
            'username': row[1],
            'name': row[2],
            'is_captain': bool(row[3]),
            'location': row[4],
        } for row in await cursor.fetchall()]
    
async def get_username(user_id: int) -> int | None:
    """Возвращает USERNAME игрока или None"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT username FROM players WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None
    

async def set_player_location(user_id: int, location: int):
    """Устанавливает локацию игрока"""
    async with get_db_connection() as conn:
        await conn.execute(
            "UPDATE players SET location = ? WHERE user_id = ?",
            (location, user_id)
        )
        await conn.commit()

async def get_player_location(user_id: int) -> int:
    """Возвращает текущую локацию игрока"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT location FROM players WHERE user_id = ?",
            (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else 1  # Возвращаем 1 если игрок не найден

async def get_players_at_location(team_id: int, location: int) -> list:
    """Возвращает всех игроков команды на указанной локации"""
    async with get_db_connection() as conn:
        cursor = await conn.execute('''
            SELECT user_id, username 
            FROM players 
            WHERE team_id = ? AND location = ?
            ORDER BY joined_at
        ''', (team_id, location))
        return await cursor.fetchall()
    
async def is_team_captain(user_id: int) -> bool:
    """Проверяет является ли игрок капитаном"""
    team_id = await get_user_team(user_id)

    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT is_captain FROM players WHERE user_id = ? AND team_id = ?",
            (user_id, team_id))
        result = await cursor.fetchone()
        
        return result[0]
