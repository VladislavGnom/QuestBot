from aiogram.fsm.state import State, StatesGroup


class QuestStates(StatesGroup):
    waiting_for_answer = State()
    waiting_for_location_confirmation = State()