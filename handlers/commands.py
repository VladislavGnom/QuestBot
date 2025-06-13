import os
import json
from random import choice
from datetime import datetime, timedelta
from aiogram import types, Dispatcher, Bot
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramForbiddenError

from texts.messages import WELCOME, HELP
from fsm.quest_logic import QuestStates, WaitForPassword
from db.help_db_commands import (add_player_to_team, get_team_players, 
                                 update_game_state, get_exist_teams, create_team_if_not_exists, 
                                 update_game_progress, generate_invite_link, create_team, join_team,
                                 get_team_name, is_admin, get_team_captain, mention_user, get_user_team,
                                 get_player_location, is_team_captain, set_player_location, create_or_upgrade_captain,
                                 create_or_upgrade_admin, get_full_location, get_location_questions,
                                 init_team_state, update_team_state, get_team_state, get_player_by_id,
                                 update_team_state, prepare_state_transfer, apply_state_transfer, get_game_state_for_team,
                                 get_status_team_game, set_lyrics_for_team)
from handlers.messages import format_game_state
from handlers.help_functions import format_timedelta
from help.logging import log_action
from handlers.timer_manager import TimerManager, QuestionTimerManager
from main import BASE_DIR, bot
from config.config import (CAPTAIN_PASSWORD, ADMIN_PASSWORD, 
                           QUESTION_TIME_LIMIT, FIRST_CLUE_OF_QUESTION,
                           SECOND_CLUE_OF_QUESTION, THIRD_CLUE_OF_QUESTION)

timer_manager = TimerManager()
question_timer_manager = QuestionTimerManager()

async def cmd_my_location(message: types.Message, state: FSMContext):
    """Показывает текущую локацию игрока"""
    await state.clear()

    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /mylocation")

    user_id = message.from_user.id
    location = await get_player_location(user_id)
    await message.answer(f"Ваша текущая локация: {location}")

async def cmd_players_locations(message: types.Message, state: FSMContext):
    """Показывает текущие локации игроков в команде"""
    await state.clear()

    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /players_locations")

    user_id = message.from_user.id
    team_id = await get_user_team(user_id=user_id)

    if not team_id:  return await message.answer(f"Ошибка: вы не в команде.")

    players = await get_team_players(team_id=team_id)
    team_name = await get_team_name(team_id=team_id)
    text = f"Данные расстановки игроков (команда - {team_name}):\n"

    for player in players:
        text += f"{player['username']} (локация {player['location']})\n"

    await message.answer(text)

async def cmd_set_location(message: types.Message, state: FSMContext):
    """Запрос на изменение локации"""
    await state.clear()

    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /setlocation")

    if not await is_team_captain(message.from_user.id):
        return await message.answer("Только капитан может менять локации!")
    
    await message.answer(
        "Введите номер новой локации:",
        reply_markup=types.ForceReply(selective=True)
    )

async def cmd_set_team_lyrics(message: types.Message, state: FSMContext):
    """Запрос на установку/изменение кричалки команды"""
    await state.clear()

    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /set_lyrics")

    if not await is_team_captain(message.from_user.id):
        return await message.answer("Только капитан может менять кричалку!")
    

    lyrics_text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    if not lyrics_text:
        return await message.answer("Укажите текст кричалки: /set_lyrics ТекстКричалки")
    
    team_id = await get_user_team(user_id=user_id)
    team_name = await get_team_name(team_id=team_id)

    status = await set_lyrics_for_team(team_id=team_id, lyrics_text=lyrics_text)

    if not status: 
        log_action(f"The lyrics fot team [team_id:{team_id}] is failed while creating by user [user_id:{user_id}].")

        return await message.answer("Ошибка при добавлении кричалки, повторите позже.")
    
    await message.answer(
        f"Кричалка для команды '{team_name}' установлена!\nКричалка:\n\n{lyrics_text}"
    )
    log_action(f"The lyrics fot team [team_id:{team_id}] is created successfully by user [user_id:{user_id}].")

async def handle_location_reply(message: types.Message, state: FSMContext):
    """Обработка ответа с номером локации"""
    await state.clear()

    if not message.reply_to_message.text == "Введите номер новой локации:":
        return
    
    try:
        new_location = int(message.text)
        if new_location < 1 or new_location > 10:  # Предположим, у нас 10 локаций
            raise ValueError
    except ValueError:
        return await message.answer("Некорректный номер локации. Введите число от 1 до 10")
    
    team_id = await get_user_team(message.from_user.id)
    players = await get_team_players(team_id)
    
    builder = InlineKeyboardBuilder()
    for player in players:
        builder.button(
            text=f"{player['username']} (локация {player['location']})", 
            callback_data=f"setloc_{player['id']}_{new_location}"
        )
    builder.adjust(1)
    
    await message.answer(
        f"Выберите игрока для перемещения на локацию {new_location}:",
        reply_markup=builder.as_markup()
    )

async def handle_player_location_change(callback: types.CallbackQuery):
    """Обработка выбора игрока для перемещения"""
    _, user_id, new_location = callback.data.split('_')
    user_id = int(user_id)
    new_location = int(new_location)
    
    await set_player_location(user_id, new_location)
    await callback.message.edit_text(
        f"Игрок перемещен на локацию {new_location}",
        reply_markup=None
    )
    await callback.answer()

    log_action(f"User [id:{user_id}] was changed location to {new_location}")

async def request_captain_role(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /become_captain")

    await message.answer(
        "Для регистрации командира введите секретный пароль:\n"
        "(запросите его у организатора)"
    )
    await state.set_state(WaitForPassword.waiting_for_captain_password)

async def process_captain_password(message: types.Message, state: FSMContext):
    if message.text != CAPTAIN_PASSWORD: 
        await message.answer("Неверный пароль!")
        return await state.clear()
    
    user_id = message.from_user.id
    if await is_team_captain(user_id):
        await message.answer("Вы уже капитан!")
        return await state.clear()
    
    team_name = f"Команда {message.from_user.full_name}"
    team_id = await create_team(message.from_user.id, team_name)
    
    await message.answer(f"Команда '{team_name}' создана!")

    success = await create_or_upgrade_captain(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        team_id=team_id
    )

    if success:
        await message.answer("Вы успешно зарегистрированы как капитан команды!")
    else:
        await message.answer("Ваши права успешно повышены")

    invite_link = await generate_invite_link(message.bot, team_id, team_name)
    
    await message.answer(
        f"Команда '{team_name}' создана!\n"
        f"Пригласительная ссылка:\n{invite_link}\n\n"
        "Отправьте эту ссылку участникам вашей команды.",
        disable_web_page_preview=True
    )
    await state.clear()

async def request_admin_role(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /become_admin")

    await message.answer(
        "Для регистрации админа введите секретный пароль:\n"
        "(запросите его у организатора)"
    )
    await state.set_state(WaitForPassword.waiting_for_admin_password)

async def process_admin_password(message: types.Message, state: FSMContext):
    if message.text != ADMIN_PASSWORD: 
        await message.answer("Неверный пароль!")
        return await state.clear()
    
    user_id = message.from_user.id
    if await is_admin(user_id):
        await message.answer("Вы уже админ!")
        return await state.clear()

    success = await create_or_upgrade_admin(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        team_id=None
    )

    if success:
        await message.answer("Вы успешно зарегистрированы как админ в системе!")
    else:
        await message.answer("Ваши права успешно повышены до уровня админа")
    
    await state.clear()

async def cmd_help(message: types.Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /help")

    await message.answer(HELP, parse_mode="HTML")

async def start_quest_for_team(team_id: int, question_id: int):
    """Инициализирует квест для команды""" 
    players = await get_team_players(team_id)
    players_ids = [pl["id"] for pl in players]    # [user_id1, user_id2, ...]
    question_deadline = datetime.now() + timedelta(minutes=QUESTION_TIME_LIMIT)
    await init_team_state(team_id=team_id, players=players_ids)

    await update_team_state(
        team_id,
        current_player_idx=0,
        players_order=json.dumps(players_ids),
        current_question_num=1,
        current_question_idx=question_id,
        correct_answers=0,
        question_deadline = question_deadline,
        status='playing',
        deadline=datetime.now() + timedelta(hours=1)  # +1 час на прохождение
    )

async def start_quest(message: types.Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    chat_id = message.chat.id

    if not await is_team_captain(user_id):
        return await message.answer("Только капитан может начинать квест!")

    team_id = await get_user_team(user_id)
    status_quest = await get_status_team_game(team_id=team_id)
    
    if status_quest is None:    # первый заход в квест
        ...
    else:
        if status_quest.lower() == 'finished':
            return await message.answer("Квест уже закончен, его нельзя начать снова! \n\nЗа подробностями обратитесь к организатору.")

    players = await get_team_players(team_id)

    log_action(f"Players from team [team_id:{team_id}]: {players}")

    if not players:
        await message.answer("В команде нет игроков!")
        return
    
    # сортировка игроков по локации
    players.sort(key=lambda pl: pl['location'])

    first_player = players[0]
    first_player_id = first_player["id"]
    
    location_id = first_player['location']
    questions = await get_location_questions(location_id=location_id)

    try:
        question = choice(questions)    # рандомный вопрос из соответственной локации
        question_id = question.get('id')
        answer_hints = json.loads(question.get('answer_hints'))
        hints_media_paths = json.loads(question.get('hints_media_paths'))
        question_media_path = question.get('media_path')
    except IndexError:    # выбрана локация для которой нет вопросов
        await message.answer("На вашу локацию нет вопросов в БД.")
        log_action(f"Error: Location [location_id:{location_id}] has not have any questions.")
        return

    try:
        path_to_question_photo = os.path.join(BASE_DIR, question_media_path)
        photo = types.FSInputFile(path_to_question_photo)
        await bot.send_photo(first_player_id, photo, caption=f"Игра началась! Ваш вопрос: {question.get('question_text')}")
    except Exception:
        await bot.send_message(
            first_player_id, 
            f"Игра началась! Ваш вопрос: {question.get('question_text')}"
        )

    # добавляем таймер для вопроса
    await question_timer_manager.add_timer(
        chat_id=chat_id,
        bot=bot,
        delay=QUESTION_TIME_LIMIT,
        message="Время вышло!",
        timer_id="question_timer"
    )


    # планируем сообщения подсказок
    try:
        fisrt_clue, second_clue, third_clue = answer_hints
        media_fc, media_sc, media_tc = hints_media_paths
        await timer_manager.add_timer(
            chat_id, 
            bot, 
            FIRST_CLUE_OF_QUESTION, 
            message=f"Подсказка #1: {fisrt_clue}",
            media_path=media_fc, 
            timer_id="clue1"
        )
        await timer_manager.add_timer(
            chat_id, 
            bot, 
            SECOND_CLUE_OF_QUESTION, 
            message=f"Подсказка #2: {second_clue}", 
            media_path=media_sc, 
            timer_id="clue2"
        )
        await timer_manager.add_timer(
            chat_id, 
            bot, 
            THIRD_CLUE_OF_QUESTION, 
            message=f"Подсказка #3: {third_clue}", 
            media_path=media_tc, 
            timer_id="clue3"
        )
    except:
        ...

    # уведомляем остальных участников команды
    await notify_team_except_current(
        team_id, 
        first_player_id, 
        "Квест начат! Первый игрок получил вопрос."
    )
    await start_quest_for_team(team_id=team_id, question_id=question_id)

    await state.set_state(QuestStates.waiting_for_answer) 
    log_action(f"User [id:{user_id}] started quest [Base Quest]")

async def send_question(player_id: int, message: types.Message, state: FSMContext): 
    user_id = message.from_user.id
    chat_id = message.chat.id

    team_id = await get_user_team(user_id=user_id)
    user_data = await get_team_state(team_id=team_id)
    team_id = user_data["team_id"]
    current_player_idx = user_data["current_player_idx"]
    players_ids=user_data["players_order"]
    question_num = user_data["current_question_num"]

    # получение экземпляров игроков
    players = [await get_player_by_id(user_id=user_id) for user_id in players_ids]
    
    current_player = players[current_player_idx]
    location_id = current_player['location']
    questions = await get_location_questions(location_id=location_id)
    question = choice(questions)    # рандомный вопрос из соответственной локации
    question_id = question.get('id')
    question_media_path = question.get('media_path')

    try:
        path_to_question_photo = os.path.join(BASE_DIR, question_media_path)
        photo = types.FSInputFile(path_to_question_photo)
        await bot.send_photo(player_id, photo, caption=f"Вопрос {question_num}: {question.get('question_text')}")
    except Exception:        
        await bot.send_message(
            player_id, 
            f"Вопрос {question_num}: {question.get('question_text')}"
        )

    question_deadline = datetime.now() + timedelta(minutes=QUESTION_TIME_LIMIT)
    answer_hints = json.loads(question.get('answer_hints'))

    # добавляем таймер для вопроса
    await question_timer_manager.add_timer(
        chat_id=chat_id,
        bot=bot,
        delay=QUESTION_TIME_LIMIT,
        message="Время вышло!",
        timer_id="question_timer"
    )

    # планируем сообщения подсказок
    try:
        fisrt_clue, second_clue, third_clue = answer_hints
        await timer_manager.add_timer(chat_id, bot, FIRST_CLUE_OF_QUESTION, message=f"Подсказка #1: {fisrt_clue}", timer_id="clue1")
        await timer_manager.add_timer(chat_id, bot, SECOND_CLUE_OF_QUESTION, message=f"Подсказка #2: {second_clue}", timer_id="clue2")
        await timer_manager.add_timer(chat_id, bot, THIRD_CLUE_OF_QUESTION, message=f"Подсказка #3: {third_clue}", timer_id="clue3")
    except:
        ...
    
    await update_team_state(
        team_id=team_id,
        current_question_idx=question_id,
        question_deadline = question_deadline,
    )

    await state.set_state(QuestStates.waiting_for_answer)

async def process_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id

    team_id = await get_user_team(user_id=user_id)
    user_data = await get_team_state(team_id=team_id)

    team_id = user_data["team_id"]
    current_player_idx = user_data["current_player_idx"]
    current_question_idx = user_data["current_question_idx"]
    question_num = user_data["current_question_num"]
    correct_answers = user_data["correct_answers"]
    players_ids = user_data["players_order"]
    is_pretend_on_right_answer = user_data["is_pretend_on_right_answer"]
    question_deadline = user_data["question_deadline"]

    is_question_deadline_passed = False

    # получение экземпляров игроков
    players = [await get_player_by_id(user_id=user_id) for user_id in players_ids]

    if message.from_user.id != players[current_player_idx].get('user_id'):
        await message.answer("Сейчас не ваш ход!")
        return
    
    
    current_player = players[current_player_idx]
    location_id = current_player["location"]
    questions = await get_location_questions(location_id=location_id)
    question = list(filter(lambda q: q["id"] == current_question_idx, questions))[0]    

    if question_deadline and datetime.fromisoformat(question_deadline) < datetime.now():
        is_question_deadline_passed = True
        await message.answer("❌ Время на ответ истекло!")
        await message.answer(f"Правильный ответ: {question.get('answer')}")
        log_action(f"User [id:{user_id}] has not any time to answer question [question_id:{question.get('id')}] in quest [Base Quest]")


    if not is_question_deadline_passed:
        if message.text.lower().strip() != question.get("answer").lower().strip():
            await message.answer("❌ Неверно! Попробуйте еще раз.")

            is_pretend_on_right_answer = False    # закрываем возможность на получения балла за вопрос

            await update_team_state(
                is_pretend_on_right_answer=is_pretend_on_right_answer, 
            )

            log_action(f"User [id:{user_id}] unsuccessfully answered question [question_id:{question.get('id')}] in quest [Base Quest]")
            return
        else:
            # Отменяем все таймеры при правильном ответе
            await timer_manager.cancel_timer(chat_id)
            await question_timer_manager.cancel_timer(message.chat.id, "question_timer")

            if is_pretend_on_right_answer:    # если первая попытка то зачисляем ответ
                correct_answers += 1

            await message.answer("✅ Верно, молодец!")
            log_action(f"User [id:{user_id}] completed question [question_id:{question.get('id')}] in quest [Base Quest]")
    
    current_player_idx += 1
    next_players = players[current_player_idx:]
    if not next_players:
        await update_team_state(
            team_id=team_id, 
            current_player_idx=current_player_idx - 1, 
            current_question_num=question_num,
            correct_answers=correct_answers,
            ended_at=datetime.now(),
            status='finished',
        )

        team_name = await get_team_name(team_id=team_id)
        user_data = await get_team_state(team_id=team_id)
        quest_time_passed = datetime.fromisoformat(user_data["ended_at"]) - datetime.fromisoformat(user_data["created_at"])
        quest_time_passed = format_timedelta(quest_time_passed)

        # Уведомляем всех участников команды
        await notify_team_except_current(
            team_id, 
            None, 
            f"🎉 Команда завершила квест!\n\nКоманда: {team_name}\nПравильных ответов: {correct_answers}/{len(players_ids)}\nВремя прохождения: {quest_time_passed}."
        )

        log_action(f"The team [team_id:{team_id}] has finished the quest [Base quest].")

        await state.clear()
        return
    
    try:
        location_data = await get_full_location(location_id=location_id)
        latitude, longtitude = location_data.get('coordinates').split(',')
        await message.answer_location(latitude=latitude, longitude=longtitude)
        await message.answer('Следующая точка маршрута!')
    except:
        await message.answer("Карта не найдена")
        

    builder = InlineKeyboardBuilder()
    builder.button(text="Я на месте", callback_data="arrived")
    
    await message.answer(
        "Нажмите кнопку по прибытии:",
        reply_markup=builder.as_markup()
    )
    
    await update_team_state(
        team_id=team_id, 
        current_player_idx=current_player_idx, 
        current_question_num=question_num + 1,
        correct_answers=correct_answers,
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
    user_id = callback.from_user.id
    team_id = await get_user_team(user_id=user_id)
    user_data = await get_team_state(team_id=team_id)
    current_player_idx = user_data["current_player_idx"]
    players_ids = user_data["players_order"]

    log_action(f"User [id:{user_id}] used /confirm_arrival")

    # получение экземпляров игроков
    players = [await get_player_by_id(user_id=user_id) for user_id in players_ids]

    target_user = players[current_player_idx]
    target_user_id = target_user.get('user_id')

    await bot.send_message(
        target_user_id, 
        f"Предыдущий игрок закончил свой ход, ваша очередь!\n\nДля перехода на свой ход используйте /accept_state"
    )

    await state.clear()
    await callback.message.answer(f"Так точно, ход передан другому игроку - @{target_user.get('username')}. Следите за состоянием игры!")
    await callback.answer()
    log_action(f"The move of game passed to next player [user_id:{target_user_id}].")

async def cmd_accept_state(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /accept_state")

    try:
        team_id = await get_user_team(user_id=user_id)
        user_data = await get_team_state(team_id=team_id)
        current_player_idx = user_data["current_player_idx"]
        players_ids = user_data["players_order"]
    except:
        await message.answer("Ошибка: вы не состоите в системе или не имеете права на эту команду.")
        return

    status_game = user_data.get('status')

    if status_game == 'finished':
        await message.answer("Ошибка: игра уже закончена.")
        return
    elif status_game == 'waiting':
        await message.answer("Ошибка: игра ещё не началась.")
        return

    # получение экземпляров игроков
    players = [await get_player_by_id(user_id=user_id) for user_id in players_ids]

    target_user = players[current_player_idx]
    target_user_id = target_user.get('user_id')

    if user_id != target_user_id: 
        await message.answer("Сейчас не ваш ход для получения состояния.")
        log_action(f"Error: Move of game is transfered unsuccessfully from player1 [user_id:{user_id}] to player2 [user_id:{target_user_id}]. The move is not of player.")
        return
    
    await message.answer(
            "Вы успешно перешли на свой ход!"
        )
    await send_question(target_user_id, message, state)

    log_action(f"Move of game is transfered successfully from player1 [user_id:{user_id}] to player2 [user_id:{target_user_id}].")

async def cmd_create_team(message: types.Message, state: FSMContext):
    """Команда для создания новой команды (только для админов)"""
    await state.clear()

    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] used /create_team")

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
    log_action(f"The team [team_id:{team_id}] is created successfully by admin [user_id:{user_id}].")

async def handle_start(message: types.Message, state: FSMContext):
    """Обработка стартовой команды с инвайт-ссылкой"""
    await state.clear()
    
    user_id = message.from_user.id

    log_action(f"User [id:{user_id}] started the bot")
    log_action(f"User [id:{user_id}] used /start")

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
            log_action(f"Invalid invite link from user [user_id:{user_id}]")
            return await message.answer("Некорректная ссылка!")
        
        success = await join_team(message, team_id, token)

        if success:
            team_name = await get_team_name(team_id)
            log_action(f"The user [user_id:{user_id}] come into team [team_id:{team_id}] successfully.")
            return await message.answer(f'Вы успешно присоединились к команде {team_name}!')
        return await message.answer("Не удалось вступить: неверный токен или вы уже в этой команде")

    # Обычный старт без ссылки
    await message.answer("Добро пожаловать! Для вступления в команду используйте инвайт-ссылку.")

async def cmd_team_status(message: types.Message):
    user_id = message.from_user.id
    team_id = await get_user_team(user_id=user_id)
    
    log_action(f"User [id:{user_id}] used /team_status")
            
    if not team_id:
        await message.answer("Вы не в команде!")
        return
        
    state = await get_game_state_for_team(team_id)
    if not state:
        await message.answer("Игра еще не начата")
        return
        
    await message.answer(
        await format_game_state(state),
        parse_mode="HTML"
    )
