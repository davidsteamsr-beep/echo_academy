from aiogram.fsm.state import State, StatesGroup


class AdminCreateDeal(StatesGroup):
    waiting_student_id = State()
    waiting_course_type = State()
    waiting_teacher_id = State()
    waiting_traffer_id = State()
    waiting_amount = State()


class AdminPayout(StatesGroup):
    waiting_user_id = State()
    waiting_amount_to_pay = State()
