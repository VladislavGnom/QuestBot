import json
import secrets
import aiosqlite
from aiogram import Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
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

async def is_admin(user_id: int):
    """Возвращает True если админ существует и пользователь им является иначе False"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT is_admin FROM players WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()

        return result[0] if result else False


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

async def get_player_by_id(user_id: int) -> dict | None:
    """Возвращает игрока по ID в виде словаря или None"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM players WHERE user_id = ?",
            (user_id,)
        )
        
        # Получаем названия колонок из описания курсора
        columns = [column[0] for column in cursor.description]
        
        # Получаем данные
        row = await cursor.fetchone()
        
        if not row:
            return None
            
        # Собираем словарь {название_колонки: значение}
        return dict(zip(columns, row))


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
        
        return result[0] if result else False

async def create_or_upgrade_captain(user_id: int, username: str, full_name: str, team_id: int) -> bool:
    """
    Создает запись капитана команды в таблице players или повышает права текущего
    """
    async with get_db_connection() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO players 
                (user_id, username, full_name, team_id, is_captain) 
                VALUES (?, ?, ?, ?, TRUE)
                """,
                (user_id, username, full_name, team_id)
            )
            await conn.commit()
            return True
        except aiosqlite.IntegrityError as e:
            await conn.execute(
                """
                UPDATE players
                SET is_captain = TRUE, team_id = ?
                """, 
                (team_id, )
            )
            await conn.commit()
            return False
    

async def create_or_upgrade_admin(user_id: int, username: str, full_name: str, team_id: int) -> bool:
    """
    Создает запись админа в таблице players или повышает права текущего
    """
    async with get_db_connection() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO players 
                (user_id, username, full_name, team_id, is_admin) 
                VALUES (?, ?, ?, ?, TRUE)
                """,
                (user_id, username, full_name, team_id)
            )
            await conn.commit()
            return True
        except aiosqlite.IntegrityError as e:
            await conn.execute(
                """
                UPDATE players
                SET is_admin = TRUE
                """
            )
            await conn.commit()
            return False
    
async def add_location(
    name: str,
    description: str,
    coordinates: str,
    image_path: str = None
) -> int:
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """INSERT INTO locations 
            (name, description, coordinates, image_path) 
            VALUES (?, ?, ?, ?)""",
            (name, description, coordinates, image_path)
        )
        await conn.commit()
        return cursor.lastrowid

async def add_question(
    location_id: int,
    question_text: str,
    answer: str,
    difficulty: int = 1,
    question_type: str = 'text'
) -> int:
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """INSERT INTO questions 
            (location_id, question_text, answer, difficulty, question_type) 
            VALUES (?, ?, ?, ?, ?)""",
            (location_id, question_text, answer, difficulty, question_type)
        )
        await conn.commit()
        return cursor.lastrowid
    
async def get_location_questions(location_id: int) -> list[dict]:
    """Возвращает список вопросов для локации в виде словарей"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """SELECT id, question_text, answer, answer_hint, 
                      difficulty, question_type, media_path, cost
               FROM questions 
               WHERE location_id = ?""",
            (location_id,)
        )
        
        # Получаем названия колонок
        columns = [column[0] for column in cursor.description]
        
        # Преобразуем каждую строку в словарь
        questions = []
        async for row in cursor:
            questions.append(dict(zip(columns, row)))
            
        return questions
    
async def get_full_location(location_id: int) -> dict:
    async with get_db_connection() as conn:
        # Получаем данные локации
        cursor = await conn.execute(
            "SELECT * FROM locations WHERE id = ?",
            (location_id,))
        location_row = await cursor.fetchone()
        
        if not location_row:
            return None
            
        # Преобразуем строку в словарь
        columns = [desc[0] for desc in cursor.description]
        location = dict(zip(columns, location_row))
        
        # Получаем вопросы локации
        cursor = await conn.execute(
            "SELECT * FROM questions WHERE location_id = ?",
            (location_id,))
        
        questions = []
        async for row in cursor:
            questions.append(dict(zip(columns, row)))
        
        location['questions'] = questions
        return location

async def create_quest(name: str, location_ids: list[int]) -> int:
    async with get_db_connection() as conn:
        # Создаем квест
        cursor = await conn.execute(
            "INSERT INTO quests (name) VALUES (?)",
            (name,))
        quest_id = cursor.lastrowid
        
        # Добавляем локации в квест
        for order, loc_id in enumerate(location_ids, 1):
            await conn.execute(
                """INSERT INTO quest_locations 
                (quest_id, location_id, order_num) 
                VALUES (?, ?, ?)""",
                (quest_id, loc_id, order))
        
        await conn.commit()
        return quest_id
    
# async def share_question_state(sender_id: int, receiver_id: int):
#     """Передает состояние вопроса другому игроку"""
#     async with get_db_connection() as conn:
#         # Получаем состояние отправителя
#         cursor = await conn.execute(
#             "SELECT question_id, progress FROM player_states WHERE user_id = ?",
#             (sender_id,)
#         )
#         state = await cursor.fetchone()
        
#         if not state:
#             return False
            
#         # Сохраняем состояние для получателя
#         await conn.execute(
#             """INSERT OR REPLACE INTO player_states 
#             (user_id, question_id, progress) 
#             VALUES (?, ?, ?)""",
#             (receiver_id, state[0], state[1])
#         )
#         await conn.commit()
#         return True

async def init_team_state(team_id: int, players: list[int]):
    """Создает начальное состояние для команды"""
    async with get_db_connection() as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO team_game_states
            (team_id, players_order, status)
            VALUES (?, ?, ?)""",
            (team_id, json.dumps(players), 'waiting')
        )
        await conn.commit()

async def update_team_state(team_id: int, **updates):
    """Обновляет несколько полей состояния команды"""
    if not updates:
        return

    set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [team_id]
    
    async with get_db_connection() as conn:
        await conn.execute(
            f"""UPDATE team_game_states
            SET {set_clause}, updated_at = datetime('now')
            WHERE team_id = ?""",
            values
        )
        await conn.commit()

async def get_team_state(team_id: int) -> dict:
    """Возвращает текущее состояние команды"""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM team_game_states WHERE team_id = ?",
            (team_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
            
        columns = [col[0] for col in cursor.description]
        state = dict(zip(columns, row))
        
        # Декодируем JSON-поля
        if state.get('players_order'):
            state['players_order'] = json.loads(state['players_order'])
            
        return state
    
async def next_player(team_id: int) -> int:
    """Передает ход следующему игроку, возвращает user_id"""
    async with get_db_connection() as conn:
        # Блокируем строку для конкурентного доступа
        await conn.execute("BEGIN IMMEDIATE")
        
        state = await get_team_state(team_id)
        if not state:
            return None
            
        players = state['players_order']
        next_idx = (state['current_player_idx'] + 1) % len(players)
        
        await conn.execute(
            """UPDATE team_game_states
            SET current_player_idx = ?, updated_at = datetime('now')
            WHERE team_id = ?""",
            (next_idx, team_id)
        )
        await conn.commit()
        
        return players[next_idx]
    
async def handle_correct_answer(team_id: int):
    """Обновляет состояние после правильного ответа"""
    async with get_db_connection() as conn:
        await conn.execute(
            """UPDATE team_game_states
            SET correct_answers = correct_answers + 1,
                current_question_idx = current_question_idx + 1,
                updated_at = datetime('now')
            WHERE team_id = ?""",
            (team_id,)
        )
        await conn.commit()


async def prepare_state_transfer(sender_id: int, receiver_id: int, state: FSMContext):
    """Подготавливает состояние для передачи другому игроку"""
    state_data = await state.get_data()
    
    async with get_db_connection() as conn:
        await conn.execute(
            """INSERT INTO state_transfers
            (sender_id, receiver_id, state_data)
            VALUES (?, ?, ?)""",
            (sender_id, receiver_id, json.dumps(state_data))
        )
        await conn.commit()
    
    # Очищаем состояние у отправителя
    await state.clear()


async def apply_state_transfer(receiver_id: int, state: FSMContext) -> bool:
    """Применяет переданное состояние для получателя"""
    async with get_db_connection() as conn:
        # Получаем последнюю передачу
        cursor = await conn.execute(
            """SELECT state_data FROM state_transfers
            WHERE receiver_id = ? AND datetime(expires_at) > datetime('now')
            ORDER BY created_at DESC LIMIT 1""",
            (receiver_id,)
        )
        transfer = await cursor.fetchone()
        
        if not transfer:
            return False
        
        # Применяем состояние
        state_data = json.loads(transfer[0])
        await state.set_data(state_data)
        
        # Удаляем использованную передачу
        await conn.execute(
            "DELETE FROM state_transfers WHERE receiver_id = ?",
            (receiver_id,)
        )
        await conn.commit()
        
        return True

async def get_game_state_for_team(team_id: int):
    """Получает полное состояние игры для команды"""
    async with get_db_connection() as conn:
        # Получаем состояние игры
        game_state = await get_team_state(team_id=team_id)

        # Получаем список игроков
        players = await get_team_players(team_id=team_id)
        
        # Получаем текущий вопрос
        question = None
        if game_state['current_question_idx']:
            cursor = await conn.execute('''
                SELECT q.*, l.name as location_name
                FROM questions q
                JOIN locations l ON q.location_id = l.id
                WHERE q.id = ?
            ''', (game_state['current_question_idx'],))

            question = await cursor.fetchone()
                
        return {
            'info': game_state,
            'players': players,
            'current_question': question
        }
