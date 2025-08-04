# QuestBot - Telegram-бот для проведения квестов �♂️🗺️

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Aiogram](https://img.shields.io/badge/Aiogram-2.x-green.svg)](https://docs.aiogram.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey.svg)](https://sqlite.org)

Бот для организации интерактивных квестов с последовательным прохождением локаций. Участники получают задания, отвечают на вопросы и перемещаются между точками, пока не завершат маршрут.

## ✨ Возможности
- ✅ Регистрация команд с подтверждением организатором
- 🏁 Пошаговое прохождение квеста (вопрос → ответ → новая локация)
- 🔄 Передача эстафеты между участниками
- 📊 Автоматический подсчет результатов
- 🗺️ Генерация маршрута между точками

## 🛠 Технологический стек
- **Язык:** Python 3.9+
- **Фреймворк:** Aiogram 3.2 (асинхронный)
- **База данных:** SQLite (aiosqlite)
- **Деплой:** Docker

## 🚀 Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/VladislavGnom/QuestBot.git
cd QuestBot
```

### 2. Настройка конфига
Откройте файл `config.py` в папке `config` и вставьте данные по примеру:
```python
BOT_TOKEN = 'YOUR_BOT_TOKEN'
DEBUG_MODE = False
CAPTAIN_PASSWORD = '1234'    # пароль для капитана
ADMIN_PASSWORD = '12345'     # пароль для админа
QUESTION_TIME_LIMIT = 5    # в минутах
FIRST_CLUE_OF_QUESTION = 1    # в минутах
SECOND_CLUE_OF_QUESTION = 3    # в минутах
THIRD_CLUE_OF_QUESTION = 4    # в минутах
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Запуск бота
```bash
python main.py
```

## 🖥 Команды для организаторов
- `/become_captain` - Запросить роль капитана 
- `/become_admin` - Запросить роль администратора 

## 👥 Команды для участников
- `/start` - начать работу с ботом
- `/create_team` - Создать новую команду (только для капитанов)
- `/begin` - Начать квест (только для капитанов)
- `/help` - справка по командам

## 📂 Структура проекта
```
QuestBot/
├── config/             # Конфигурационные файлы
├── db/                 # Работа с базой данных SQLite
├── fsm/                # Состояния используемые в боте
├── handlers/           # Обработчики сообщений
├── help/               # Вспомогательные утилиты(логирование)
├── texts/              # Текста для сообщений
├── keyboards.py        # Клавиатуры
├── main.py             # Точка входа
└── README.md           # Этот файл
```
