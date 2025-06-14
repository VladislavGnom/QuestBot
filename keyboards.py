from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

start_markup = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Зарегистрироваться как капитан", callback_data="sign_up_as_captain")],
    [InlineKeyboardButton(text="Зарегистрироваться как участник", callback_data="sign_up_as_player")],
])

default_user_markup = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Моя локация"), KeyboardButton(text="Расстановка игроков"), KeyboardButton(text="Получить текст кричалки")],
], resize_keyboard=True)

captain_user_markup = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Моя локация"), KeyboardButton(text="Расстановка игроков"), KeyboardButton(text="Получить текст кричалки")],
    [KeyboardButton(text="Установить кричалку"), KeyboardButton(text="Поменять расстановку"), KeyboardButton(text="Начать квест")],
    [KeyboardButton(text="Начать квест в тестовом режиме")]
], resize_keyboard=True)

accept_state_markup = InlineKeyboardMarkup(keyboard=[
    [InlineKeyboardButton(text="Принять ход", callback_data="accept_state")]
])