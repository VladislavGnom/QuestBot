import asyncio
from aiogram import Bot

class TimerManager:
    def __init__(self):
        self.timers = {}  # {chat_id: {timer_id: task}}
    
    async def add_timer(self, chat_id: int, bot: Bot, delay: int, message: str, timer_id: str):
        """Добавление нового таймера"""
        await self.cancel_timer(chat_id, timer_id)
        
        task = asyncio.create_task(
            self._send_timed_message(chat_id, bot, delay, message, timer_id)
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
    
    async def _send_timed_message(self, chat_id: int, bot: Bot, delay: int, message: str, timer_id: str):
        try:
            clue_num = timer_id[-1:]
            await asyncio.sleep(delay * 60)    # минуты
            await bot.send_message(chat_id, f"Подсказка #{clue_num}: {message}")
        except asyncio.CancelledError:
            pass
        finally:
            if chat_id in self.timers and timer_id in self.timers[chat_id]:
                del self.timers[chat_id][timer_id]
