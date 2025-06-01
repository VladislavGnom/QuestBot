import json
from aiogram import types
from db.help_db_commands import get_location_questions, get_team_name

async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

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