from aiogram import types

async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")
