import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, types
from main import BASE_DIR

class TimerManager:
    def __init__(self):
        self.timers = {}  # {chat_id: {timer_id: task}}
    
    async def add_timer(self, chat_id: int, bot: Bot, delay: int, message: str, media_path: str, timer_id: str):
        """Добавление нового таймера"""
        await self.cancel_timer(chat_id, timer_id)
        
        task = asyncio.create_task(
            self._send_timed_message(chat_id, bot, delay, message, media_path, timer_id)
        )
        
        if chat_id not in self.timers:
            self.timers[chat_id] = {}
        self.timers[chat_id][timer_id] = task

    async def cancel_timer(self, chat_id: int, timer_id: str = None):
        """Отмена таймеров"""
        if chat_id not in self.timers:
            return
        
        if timer_id is None:
            # Отмена всех таймеров
            for task in self.timers[chat_id].values():
                task.cancel()
            self.timers[chat_id].clear()
        else:
            # Отмена конкретного таймера
            if timer_id in self.timers[chat_id]:
                self.timers[chat_id][timer_id].cancel()
                del self.timers[chat_id][timer_id]
    
    async def _send_timed_message(self, chat_id: int, bot: Bot, delay: int, message: str, media_path: str, timer_id: str):
        try:
            await asyncio.sleep(delay * 60)    # минуты

            if media_path:
                path_to_question_photo = os.path.join(BASE_DIR, media_path)
                photo = types.FSInputFile(path_to_question_photo)
                await bot.send_photo(chat_id, photo)

            await bot.send_message(chat_id, message)
        except (asyncio.CancelledError | Exception):
            pass
        finally:
            if chat_id in self.timers and timer_id in self.timers[chat_id]:
                del self.timers[chat_id][timer_id]


class QuestionTimerManager:
    def __init__(self):
        self.timers = {}  # {chat_id: {timer_id: (task, message_id, end_time)}}
    
    async def add_timer(self, chat_id: int, bot: Bot, delay: int, message: str, timer_id: str):
        """Добавление нового таймера с обновляемым сообщением"""
        await self.cancel_timer(chat_id, timer_id)
        
        end_time = datetime.now() + timedelta(minutes=delay)
        initial_text = f"⏳ Таймер: {delay} мин.\nОсталось: {delay}:00"
        
        # Отправляем начальное сообщение
        msg = await bot.send_message(chat_id, initial_text)
        
        # Создаем задачу для обновления сообщения
        task = asyncio.create_task(
            self._update_timer_message(chat_id, bot, msg.message_id, end_time, timer_id, message)
        )
        
        if chat_id not in self.timers:
            self.timers[chat_id] = {}
        self.timers[chat_id][timer_id] = (task, msg.message_id, end_time)
    
    async def _update_timer_message(self, chat_id: int, bot: Bot, message_id: int, 
                                 end_time: datetime, timer_id: str, final_message: str):
        """Обновление сообщения с таймером"""
        while True:
            try:
                now = datetime.now()
                remaining = end_time - now
                
                if remaining.total_seconds() <= 0:
                    await bot.edit_message_text(
                        f"⏰ {final_message}",
                        chat_id=chat_id,
                        message_id=message_id
                    )
                    self._cleanup_timer(chat_id, timer_id)
                    break
                
                # Форматируем оставшееся время
                total_seconds = int(remaining.total_seconds())
                minutes, seconds = divmod(total_seconds, 60)
                time_str = f"{minutes}:{seconds:02d}"
                
                await bot.edit_message_text(
                    f"⏳ Таймер \nОсталось: {time_str}",
                    chat_id=chat_id,
                    message_id=message_id
                )
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Ошибка в таймере: {e}")
                self._cleanup_timer(chat_id, timer_id)
                break
    
    def _cleanup_timer(self, chat_id: int, timer_id: str):
        """Очистка таймера из словаря"""
        if chat_id in self.timers and timer_id in self.timers[chat_id]:
            del self.timers[chat_id][timer_id]
    
    async def cancel_timer(self, chat_id: int, timer_id: str = None):
        """Отмена таймеров"""
        if chat_id not in self.timers:
            return
        
        if timer_id is None:
            # Отмена всех таймеров в чате
            for timer_data in self.timers[chat_id].values():
                timer_data[0].cancel()  # task
            self.timers[chat_id].clear()
        else:
            # Отмена конкретного таймера
            if timer_id in self.timers[chat_id]:
                self.timers[chat_id][timer_id][0].cancel()
                self._cleanup_timer(chat_id, timer_id)
