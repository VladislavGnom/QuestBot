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
