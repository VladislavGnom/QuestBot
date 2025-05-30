from aiogram.fsm.state import State, StatesGroup


class QuestStates(StatesGroup):
    waiting_for_answer = State()
    waiting_for_location_confirmation = State()


class WaitForPassword(StatesGroup):
    waiting_for_captain_password = State()
    waiting_for_admin_password = State()
    