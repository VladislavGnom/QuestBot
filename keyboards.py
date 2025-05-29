from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    markup = [
        [KeyboardButton(text='Button 1'), KeyboardButton(text='Button 2')]
    ]

    return ReplyKeyboardMarkup(keyboard=markup, resize_keyboard=True)
