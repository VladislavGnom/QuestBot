from datetime import datetime, timedelta
import asyncio
from aiogram import Bot


async def schedule_message(bot: Bot, chat_id: int, delay_minutes: int, message_text: str):
    """Запланировать отправку сообщения через указанное время"""
    await asyncio.sleep(delay_minutes * 60)
    try:
        await bot.send_message(chat_id=chat_id, text=message_text)
    except Exception as e:
        print(f"Не удалось отправить сообщение: {e}")

