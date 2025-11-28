# app/bot/states.py
from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    STANDARD = State()          # standard_mode
    PHOTO_COMMENT = State()     # photo_comment_input
    PROMO = State()             # promo_input
    CALORIES_PLAN = State()     # calories_plan_input
    ADMIN = State()             # admin_mode
    LIMIT_RESET = State()       # limit_reset_input
    PROMO_GENERATE = State()    # promo_generate_input
