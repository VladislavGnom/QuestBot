from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramForbiddenError

from texts.messages import WELCOME, HELP
from fsm.quest_logic import QuestStates
from db.help_db_commands import (add_player_to_team, get_team_players, 
                                 update_game_state, get_exist_teams, create_team_if_not_exists, 
                                 update_game_progress, generate_invite_link, create_team, join_team,
                                 get_team_name, is_admin, get_team_captain, mention_user, get_user_team)
from main import BASE_DIR, bot


# Пример данных квеста (можно тоже хранить в БД)
QUEST_DATA = {
    1: {  # team_id
        "player_1": {
            "question": "Что растёт в огороде?",
            "answers": ["лук", "морковь", "картошка"],
            "next_player": "player_2",
            "image": f"{BASE_DIR}/images/map1.png",
        },
        "player_2": {
            "question": "Какой металл самый легкий?",
            "answers": ["алюминий", "литий", "магний"],
            "next_player": None,
            "image": f"{BASE_DIR}/images/map2.png",
        },
    }
}

# async def cmd_start(message: types.Message, state: FSMContext):
#     await state.clear()
#     team_id = 1
#     team_name = 'fisrt'

#     if team_id not in await get_exist_teams():
#         team_id, created = await create_team_if_not_exists(team_name)
#         if not created:
#             await message.answer("Ошибка: команда не создана.")
#             return
            
#     if message.from_user.id not in await get_team_players(team_id):
#         await add_player_to_team(
#             message.from_user.id,
#             message.from_user.username,
#             team_id
#         )
#         await message.answer("Вы в команде! Ожидайте начала игры.")
#     else:
#         await message.answer("Вы уже в команде!")

async def cmd_show_player_number_position_in_team(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    

async def cmd_help(message: types.Message):
    await message.answer(HELP)

async def start_quest(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    team_id = await get_user_team(user_id)
    players = await get_team_players(team_id)

    if not players:
        await message.answer("В команде нет игроков!")
        return
    
    first_player = players[0]
    first_player_id = first_player["id"]

    await update_game_progress(team_id, first_player_id, 1, "playing")
    
    question = QUEST_DATA[team_id]["player_1"]["question"]
    await bot.send_message(
        first_player_id, 
        f"Игра началась! Ваш вопрос: {question}"
    )

    # Уведомляем остальных участников команды
    await notify_team_except_current(
        team_id, 
        first_player_id, 
        "Квест начат! Первый игрок получил вопрос."
    )
    
    await state.update_data(
        team_id=team_id,
        current_player_idx=0,
        question_num=1,
        players_order=players  # Сохраняем порядок игроков
    )
    await state.set_state(QuestStates.waiting_for_answer) 

async def send_question(player_id: int, message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    team_id = user_data["team_id"]
    question_num = user_data["question_num"]
    
    question_data = QUEST_DATA[team_id][f"player_{question_num}"]

    await bot.send_message(
        player_id, 
        f"Вопрос {question_num}: {question_data['question']}"
    )
    
    await state.update_data(
        correct_answers=question_data["answers"],
        next_player=question_data["next_player"],
        deadline=datetime.now() + timedelta(minutes=5)
    )
    await state.set_state(QuestStates.waiting_for_answer)

async def process_answer(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    team_id = user_data["team_id"]
    current_idx = user_data["current_player_idx"]
    question_num = user_data["question_num"]
    players = user_data["players_order"]
    
    if message.from_user.id != players[current_idx].get('id'):
        await message.answer("Сейчас не ваш ход!")
        return
    
    question_data = QUEST_DATA[team_id][f"player_{question_num}"]
    
    if message.text.lower() not in [a.lower() for a in question_data["answers"]]:
        await message.answer("❌ Неверно! Попробуйте еще раз.")
        return
    
    next_player = question_data["next_player"]
    if not next_player:
        await message.answer("🎉 Команда завершила квест!")
        await state.clear()
        return
    
    next_player_num = int(next_player.split("_")[1])
    if next_player_num > len(players):
        await message.answer("Ошибка: нет следующего игрока")
        return
        
    await update_game_progress(
        team_id, 
        players[next_player_num-1].get('id'),
        next_player_num,
        "playing"
    )
    
    try:
        photo = types.FSInputFile(question_data["image"])
        await message.answer_photo(photo, caption="Следующая точка маршрута!")
    except FileNotFoundError:
        await message.answer("Карта не найдена")
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Я на месте", callback_data="arrived")
    
    await message.answer(
        "Нажмите кнопку по прибытии:",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(
        current_player_idx=next_player_num-1,
        question_num=next_player_num
    )
    await state.set_state(QuestStates.waiting_for_location_confirmation)

async def notify_team_except_current(team_id: int, current_player_id: int, message_text: str):
    players = await get_team_players(team_id)
    
    # Отправляем сообщение всем, кроме текущего игрока
    for player_data in players:
        player_id = player_data.get('id')
        if player_id != current_player_id:
            try:
                await bot.send_message(player_id, message_text)
            except Exception as e:
                print(f"Не удалось отправить сообщение игроку {player_id}: {e}")
            except TelegramForbiddenError:
                print(f"Пользователь {player_id} не начал диалог с ботом")

async def confirm_arrival(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await send_question(callback.message.from_user.id, callback.message, state)


async def cmd_create_team(message: types.Message):
    """Команда для создания новой команды (только для админов)"""
    if not await is_admin(message.from_user.id):  # Ваша функция проверки админа
        return await message.answer("Только админы могут создавать команды!")
    
    team_name = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not team_name:
        return await message.answer("Укажите название команды: /create_team НазваниеКоманды")
    
    team_id = await create_team(message.from_user.id, team_name)
    invite_link = await generate_invite_link(message.bot, team_id, team_name)
    
    await message.answer(
        f"Команда '{team_name}' создана!\n"
        f"Пригласительная ссылка:\n{invite_link}\n\n"
        "Отправьте эту ссылку участникам вашей команды.",
        disable_web_page_preview=True
    )

async def handle_start(message: types.Message, state: FSMContext):
    """Обработка стартовой команды с инвайт-ссылкой"""
    await state.clear()

    user_id = message.from_user.id
    
    # Проверяем, состоит ли пользователь уже в какой-либо команде
    current_team = await get_user_team(user_id)

    if current_team:
        # Пользователь уже в команде - особое сообщение
        team_name = await get_team_name(current_team)
        captain_id = await get_team_captain(current_team)
        
        text = (
            f"Вы уже состоите в команде '{team_name}'\n\n"
            "Ожидайте начала квеста от капитана команды.\n"
            f"Капитан: {await mention_user(captain_id)}"
        )
            
        return await message.answer(text)

    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    
    if args and args.startswith('join_'):
        _, team_id, token = args.split('_', maxsplit=2)[:3]
        try:
            team_id = int(team_id)
        except ValueError:
            return await message.answer("Некорректная ссылка!")
        
        success = await join_team(message, team_id, token)

        if success:
            team_name = await get_team_name(team_id)
            return await message.answer(f'Вы успешно присоединились к команде {team_name}!')
        return await message.answer("Не удалось вступить: неверный токен или вы уже в этой команде")
    
    # Обычный старт без ссылки
    await message.answer("Добро пожаловать! Для вступления в команду используйте инвайт-ссылку.")
