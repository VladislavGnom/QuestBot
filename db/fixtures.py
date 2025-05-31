import json
import aiosqlite
from pathlib import Path

async def load_fixtures_from_json(db_path: str = 'quest_bot.db', 
                                json_path: str = 'db/quest_fixtures.json'):
    # Проверяем существование файла
    if not Path(json_path).exists():
        raise FileNotFoundError(f"Fixture file {json_path} not found")
    
    # Читаем JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        
        # Заполняем таблицы
        # Правильный порядок загрузки:
        await _load_table(conn, "locations", data["locations"])
        await _load_table(conn, "quests", data["quests"])
        await _load_table(conn, "questions", data["questions"])
        await _load_table(conn, "quest_locations", data["quest_locations"])
        
        await conn.commit()
        print(f"✅ Успешно загружено: "
              f"{len(data['locations'])} локаций, "
              f"{len(data['questions'])} вопросов, "
              f"{len(data['quests'])} квестов")

async def _load_table(conn, table_name: str, items: list):
    if not items:
        return
    
    # Получаем список колонок из первой записи
    columns = list(items[0].keys())
    placeholders = ', '.join([':' + col for col in columns])
    
    # Удаляем существующие записи
    await conn.execute(f"DELETE FROM {table_name}")

    await conn.commit()
    
    # Вставляем новые данные
    await conn.executemany(
        f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})",
        items
    )