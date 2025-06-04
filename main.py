import os
import logging
import asyncio
from aiogram import F
from aiogram import Dispatcher, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from db.database import init_db

import handlers.commands as handlers
from config.config import BOT_TOKEN, DEBUG_MODE
from handlers.messages import invalid_command
from fsm.quest_logic import QuestStates, WaitForPassword

BASE_DIR = os.path.dirname(__file__)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
logger = logging.getLogger(__name__)

def register_handlers(dp: Dispatcher):
    dp.message.register(handlers.process_captain_password, StateFilter(WaitForPassword.waiting_for_captain_password))
    dp.message.register(handlers.process_admin_password, StateFilter(WaitForPassword.waiting_for_admin_password))
    dp.message.register(handlers.process_answer, StateFilter(QuestStates.waiting_for_answer))
    dp.callback_query.register(handlers.confirm_arrival, StateFilter(QuestStates.waiting_for_location_confirmation), F.data == 'arrived')
    dp.callback_query.register(handlers.handle_player_location_change, F.data.startswith("setloc_"))
    dp.message.register(handlers.handle_location_reply, F.reply_to_message & F.text.isdigit())
    dp.message.register(handlers.handle_start, Command("start"))
    dp.message.register(handlers.start_quest, Command('begin'))
    dp.message.register(handlers.cmd_create_team, Command("create_team"))
    dp.message.register(handlers.cmd_team_status, Command("team_status"))
    dp.message.register(handlers.cmd_help, Command('help'))
    dp.message.register(handlers.cmd_accept_state, Command("accept_state"))
    dp.message.register(handlers.request_captain_role, Command("become_captain"))
    dp.message.register(handlers.request_admin_role, Command("become_admin"))
    dp.message.register(handlers.cmd_my_location, Command("mylocation"))
    dp.message.register(handlers.cmd_set_location, Command("setlocation"))
    dp.message.register(invalid_command, F.text)

async def on_startup():
    register_handlers(dp=dp)

    # подключение логов
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('mainapp.log'),  # Log to file
            logging.StreamHandler()              # Also print to console
        ]
        )

    # Инициализация БД при старте
    await init_db()
    
    if DEBUG_MODE:
        from db.fixtures import load_fixtures_from_json
        try:
            await load_fixtures_from_json()
        except Exception as e:
            print(f"⚠️ Ошибка загрузки фикстур: {e}")

async def main():
    await on_startup()
    await dp.start_polling(bot)


if __name__ == '__main__':
    print('Бот стартует...')
    try:
        print('Бот запущен')
        asyncio.run(main())
    except InterruptedError:
        print('Бот выключен')
