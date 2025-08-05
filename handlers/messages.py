import json
from aiogram import types
from db.help_db_commands import get_location_questions, get_team_name, is_team_captain
from keyboards import captain_user_markup, default_user_markup

async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

async def invalid_command(message: types.Message):
    message_text = message.text
    user_id = message.from_user.id

    current_keyboard = captain_user_markup if is_team_captain(user_id) else default_user_markup

    if message_text.startswith('/'):
        await message.answer(f"Ошибка! Неверная команда - {message.text}")
    else:
        await message.answer(f"Ошибка! Я не понимаю ваш запрос: {message.text}\n\nВоспользуйтесь /help для ознакомления со мной.")

    # Отправляем новое сообщение с reply-клавиатурой
    await message.answer(
        "Выберите следующее действие:",
        reply_markup=current_keyboard
    )

async def format_game_state(state: dict) -> str:
    """Форматирует состояние игры в читаемый текст"""
    info = state['info']
    players = state['players']
    current_player_id = info['players_order'][info['current_player_idx']]
    current_player = next((p for p in players if p['id'] == current_player_id), None)

    questions = await get_location_questions(current_player['location'])
    question = list(filter(lambda q: q["id"] == info['current_question_idx'], questions))[0]
    team_name = await get_team_name(team_id=info['team_id'])

    text = [
        f"<b>Команда:</b> {team_name}",
        f"<b>Статус:</b> {info['status'].upper()}",
        f"<b>Вопрос:</b> {info['current_question_num']}/{len(players)}",
        f"<b>Правильных ответов:</b> {info['correct_answers']}",
        "",
        f"<b>Текущий игрок:</b> @{current_player['username'] if current_player else '?'}",
        f"<b>Локация:</b> {current_player['location'] if current_player else '?'}",
        "",
        f"<b>Текущий вопрос:</b>",
        f"{question['question_text'] if question else 'Не задан'}"
    ]
    
    return "\n".join(text)