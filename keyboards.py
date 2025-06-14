from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

start_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Зарегистрироваться как капитан", callback_data="sign_up_as_captain")],
    [InlineKeyboardButton(text="Зарегистрироваться как участник", callback_data="sign_up_as_player")]
])

default_user_markup = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Моя локация"), KeyboardButton(text="Расстановка игроков"), KeyboardButton(text="Получить текст кричалки")],
], resize_keyboard=True)

captain_user_markup = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Моя локация"), KeyboardButton(text="Расстановка игроков"), KeyboardButton(text="Получить текст кричалки")],
    [KeyboardButton(text="Установить кричалку"), KeyboardButton(text="Поменять расстановку"), KeyboardButton(text="Начать квест")],
], resize_keyboard=True)
