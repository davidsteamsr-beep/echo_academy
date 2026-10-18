from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.database import Course, User, rub

BTN_LEADS = "Все лиды"
BTN_CREATE = "Создать сделку"
BTN_PAYOUTS = "Выплаты"
BTN_SYSTEM = "Статистика системы"
BTN_LINK = "Моя ссылка"
BTN_STATS = "Статистика"
BTN_BALANCE = "Баланс"
BTN_STUDENTS = "Ученики"
BTN_COURSES = "Мои курсы"
BTN_PAY = "Оплатить"
BTN_CANCEL = "Отмена"


def get_admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LEADS), KeyboardButton(text=BTN_CREATE)],
            [KeyboardButton(text=BTN_PAYOUTS), KeyboardButton(text=BTN_SYSTEM)],
        ],
        resize_keyboard=True,
    )


def get_traffer_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LINK), KeyboardButton(text=BTN_STATS)],
            [KeyboardButton(text=BTN_BALANCE)],
        ],
        resize_keyboard=True,
    )


def get_teacher_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_STUDENTS), KeyboardButton(text=BTN_BALANCE)]],
        resize_keyboard=True,
    )


def get_student_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_COURSES), KeyboardButton(text=BTN_PAY)]],
        resize_keyboard=True,
    )


def get_main_menu(role: str) -> ReplyKeyboardMarkup:
    if role == "admin":
        return get_admin_menu()
    if role == "traffer":
        return get_traffer_menu()
    if role == "teacher":
        return get_teacher_menu()
    return get_student_menu()


def get_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_CANCEL, callback_data="cancel")]]
    )


def get_course_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Индивидуально · 90к", callback_data="course:individual")],
            [InlineKeyboardButton(text="Группа · 180к", callback_data="course:group")],
            [InlineKeyboardButton(text=BTN_CANCEL, callback_data="cancel")],
        ]
    )


def get_confirm_deal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить сделку", callback_data="deal:confirm")],
            [InlineKeyboardButton(text=BTN_CANCEL, callback_data="cancel")],
        ]
    )


def get_courses_kb(courses: list[Course]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{course.title} · {rub(course.base_price)}", callback_data=f"buy:{course.id}")]
        for course in courses
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_pay_kb(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"pay:{lead_id}")]
        for lead_id, title in items
    ]
    rows.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_payouts_kb(users: list[User]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Выплатить · {user.full_name} · {rub(user.balance)}", callback_data=f"payout:{user.id}")]
        for user in users[:25]
    ]
    rows.append([InlineKeyboardButton(text="Ввести ID вручную", callback_data="payout:manual")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
