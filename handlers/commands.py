from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts.messages import WELCOME, HELP
from fsm.quest_logic import QuestStates
from db.help_db_commands import (add_player_to_team, get_team_players, 
                                 update_game_state, get_exist_teams, create_team_if_not_exists, update_game_progress)
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
        # ... остальные вопросы
    }
}

# QUEST_DATA = {
#     1: {
#         "question": "Что растёт в огороде?",
#         "answers": ["лук", "морковь", "картошка"],
#         "image": f"{BASE_DIR}/images/map1.png",
#         "next_step": 2
#     },
#     2: {
#         "question": "Какой металл самый легкий?",
#         "answers": ["алюминий", "литий", "магний"],
#         "image": f"{BASE_DIR}/images/map2.png",
#         "next_step": None  # Конец квеста
#     }
# }

async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    team_id = 1

    if team_id not in await get_exist_teams():
        team_id, created = await create_team_if_not_exists('first')
        if created:
            await add_player_to_team(
                    message.from_user.id,
                    message.from_user.username,
                    team_id
                )
            await message.answer("Вы создали команду! Ожидаем начала игры.")
        else:
            await message.answer("Ошибка: команда не создана.")
    else:
        if message.from_user.id not in await get_team_players(team_id):
            # Для примера - добавляем в команду с ID 1
            await add_player_to_team(
                message.from_user.id,
                message.from_user.username,
                team_id
            )
            await message.answer("Вы добавлены в команду! Ожидайте начала игры.")
        else:
            await message.answer("Вы уже в команде!")

    # builder = InlineKeyboardBuilder()
    # builder.add(types.InlineKeyboardButton(
    #     text="Начать квест",
    #     callback_data="start_quest"
    # ))
    # await message.answer(
    #     WELCOME.format(name=message.from_user.first_name),
    #     reply_markup=builder.as_markup()
    # )

async def cmd_help(message: types.Message):
    await message.answer(HELP)

async def start_quest(message: types.Message, state: FSMContext):
    team_id = 1
    players = await get_team_players(team_id)
    
    if not players:
        await message.answer("В команде нет игроков!")
        return
    
    # Устанавливаем первого игрока
    first_player = players[0]
    await update_game_progress(team_id, first_player, 1, "playing")
    
    # Отправляем вопрос первому игроку
    question = QUEST_DATA[team_id]["player_1"]["question"]
    await bot.send_message(first_player, f"Игра началась! Ваш вопрос: {question}")
    
    # Обновляем состояние для первого игрока
    await state.update_data(
        team_id=team_id,
        current_player_idx=0,
        question_num=1
    )
    await state.set_state(QuestStates.waiting_for_answer)
    
    await message.answer("Квест начат! Первый игрок получил вопрос.")
    
    # team_id = 1
    # players = await get_team_players(team_id)
    
    # if not players:
    #     await message.answer("В команде нет игроков!")
    #     return
    
    # await update_game_state(team_id, 0, "playing")
    # first_player = players[0]
    
    # await bot.send_message(
    #     first_player,
    #     f"Игра началась! Ваш вопрос: {QUEST_DATA[team_id]['player_1']['question']}"
    # )
    # await message.answer("Квест начат! Первый игрок получил вопрос.")

    # await callback.message.answer('Хорошо! Приступаем...')
    # await callback.answer()
    # await send_question(1, callback.message, state)

async def send_question(message: types.Message, state: FSMContext):
    # Получаем данные из состояния
    user_data = await state.get_data()
    team_id = user_data["team_id"]
    current_idx = user_data["current_player_idx"]
    question_num = user_data["question_num"]
    
    # Получаем данные вопроса для текущего игрока
    question_data = QUEST_DATA[team_id][f"player_{question_num}"]
    
    # Отправляем вопрос
    await message.answer(f"Вопрос {question_num}: {question_data['question']}")
    
    # Обновляем состояние с временем ответа
    await state.update_data(
        correct_answers=question_data["answers"],
        next_player=question_data["next_player"],
        deadline=datetime.now() + timedelta(minutes=5)
    )
    
    # Устанавливаем состояние ожидания ответа
    await state.set_state(QuestStates.waiting_for_answer)

async def process_answer(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    team_id = user_data["team_id"]
    current_idx = user_data["current_player_idx"]
    question_num = user_data["question_num"]
    
    players = await get_team_players(team_id)
    current_player = players[current_idx]
    
    # Проверяем, что ответил текущий игрок
    if message.from_user.id != current_player:
        await message.answer("Сейчас не ваш ход!")
        return
    
    question_data = QUEST_DATA[team_id][f"player_{question_num}"]
    
    # Проверка правильного ответа
    if message.text.lower() in [a.lower() for a in question_data["answers"]]:
        # Определяем следующего игрока
        next_player_num = int(question_data["next_player"].split("_")[1])
        
        if next_player_num > len(players):
            await message.answer("🎉 Команда завершила квест!")
            await state.clear()
            return
            
        next_player = players[next_player_num - 1]
        
        # Обновляем прогресс
        await update_game_progress(
            team_id, 
            next_player,
            next_player_num,
            "playing"
        )
        
        # Отправляем карту
        try:
            photo = types.FSInputFile(question_data["image"])
            await message.answer_photo(photo, caption="Следующая точка маршрута!")
        except FileNotFoundError:
            await message.answer("Карта не найдена")
        
        # Кнопка подтверждения прибытия
        builder = InlineKeyboardBuilder()
        builder.button(text="Я на месте", callback_data="arrived")
        
        await message.answer(
            "Нажмите кнопку по прибытии:",
            reply_markup=builder.as_markup()
        )
        
        await state.update_data(
            current_player_idx=next_player_num - 1,
            question_num=next_player_num
        )
        await state.set_state(QuestStates.waiting_for_location_confirmation)
    else:
        await message.answer("❌ Неверно! Попробуйте еще раз.")

        
    # user_data = await state.get_data()
    
    # # Проверяем время ответа
    # if datetime.now() > user_data["deadline"]:
    #     correct_answers = ", ".join(user_data["correct_answers"])
    #     await message.answer(f"Время вышло! Правильные ответы: {correct_answers}")
    #     await proceed_to_next_step(user_data["next_step"], message, state)
    #     return
    
    # # Проверяем правильность ответа
    # if message.text.lower() in [ans.lower() for ans in user_data["correct_answers"]]:
    #     await message.answer("✅ Правильно! Поздравляем!")
    #     await proceed_to_next_step(user_data["next_step"], message, state)
    # else:
    #     await message.answer("❌ Неверно. Попробуйте ещё раз.")

async def proceed_to_next_step(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    next_player = user_data.get("next_player")
    
    if not next_player:
        await message.answer("🎉 Квест завершён! Спасибо за участие!")
        await state.clear()
        return
    
    next_player_num = int(next_player.split("_")[1])
    
    # Обновляем данные в состоянии
    await state.update_data(
        current_player_idx=next_player_num - 1,
        question_num=next_player_num
    )
    
    # Отправляем карту местности
    team_id = user_data["team_id"]
    question_data = QUEST_DATA[team_id][f"player_{next_player_num}"]
    
    try:
        photo = types.FSInputFile(question_data["image"])
        await message.answer_photo(photo, caption="Вот следующая точка вашего квеста!")
    except FileNotFoundError:
        await message.answer("Ошибка: файл с картой не найден")
    
    # Кнопка подтверждения прибытия
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Я прибыл на место",
        callback_data="arrived"
    ))
    
    await message.answer(
        "Нажмите кнопку, когда доберётесь до места:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(QuestStates.waiting_for_location_confirmation)

async def confirm_arrival(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await send_question(callback.message, state)
