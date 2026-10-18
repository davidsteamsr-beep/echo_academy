from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import (
    Role,
    get_user,
    list_lead_rows,
    open_deal,
    payout,
    rub,
    set_role,
    split_group_bundle,
    split_individual,
    system_stats,
    users_with_balance,
)
from bot.filters import IsAdmin
from bot.handlers.common import notify
from bot.keyboards import (
    BTN_CREATE,
    BTN_LEADS,
    BTN_PAYOUTS,
    BTN_SYSTEM,
    get_admin_menu,
    get_cancel_kb,
    get_confirm_deal_kb,
    get_course_type_kb,
    get_payouts_kb,
)
from bot.states import AdminCreateDeal, AdminPayout

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text == BTN_LEADS)
async def all_leads(message: Message) -> None:
    rows = await list_lead_rows()
    if not rows:
        await message.answer("Лидов нет.")
        return
    lines = [
        f"#{lead.id} | {name} | {title} | {lead.status.value} | {traffer if traffer else '—'}"
        for lead, name, title, traffer in rows
    ]
    text = "\n".join(lines)
    for chunk in _chunks(text):
        await message.answer(chunk)


@router.message(F.text == BTN_SYSTEM)
async def stats(message: Message) -> None:
    await message.answer(await system_stats() + "\n\nРоль: /role <telegram_id> <admin|traffer|teacher|student>")


@router.message(Command("role"))
async def cmd_role(message: Message, command: CommandObject, bot: Bot) -> None:
    parts = (command.args or "").split()
    if len(parts) != 2 or parts[1] not in Role._value2member_map_:
        await message.answer("Формат: /role 123456789 teacher")
        return
    try:
        user_id = int(parts[0])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    updated = await set_role(user_id, Role(parts[1]))
    if updated is None:
        await message.answer("Пользователь не найден. Пусть сначала нажмёт /start.")
        return
    await message.answer(f"{updated.full_name} теперь {updated.role.value}.")
    await notify(bot, updated.id, f"Ваша роль в ECHO Academy: {updated.role.value}. Нажмите /start.")


@router.message(F.text == BTN_CREATE)
async def create_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminCreateDeal.waiting_student_id)
    await message.answer("Введите Telegram ID ученика.", reply_markup=get_cancel_kb())


@router.message(AdminCreateDeal.waiting_student_id)
async def take_student(message: Message, state: FSMContext) -> None:
    user_id = _parse_id(message.text or "")
    if user_id is None:
        await message.answer("Нужен числовой ID.", reply_markup=get_cancel_kb())
        return
    user = await get_user(user_id)
    if user is None or user.role != Role.student:
        await message.answer("Ученик с таким ID не найден.", reply_markup=get_cancel_kb())
        return
    await state.update_data(student_id=user.id, student_name=user.full_name)
    await state.set_state(AdminCreateDeal.waiting_course_type)
    await message.answer(f"{user.full_name}. Тип курса:", reply_markup=get_course_type_kb())


@router.callback_query(AdminCreateDeal.waiting_course_type, F.data.startswith("course:"))
async def take_course(callback: CallbackQuery, state: FSMContext) -> None:
    course_type = (callback.data or "").split(":", 1)[1]
    await state.update_data(course_type=course_type)
    await state.set_state(AdminCreateDeal.waiting_teacher_id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer("Введите ID преподавателя.", reply_markup=get_cancel_kb())


@router.message(AdminCreateDeal.waiting_teacher_id)
async def take_teacher(message: Message, state: FSMContext) -> None:
    user_id = _parse_id(message.text or "")
    user = await get_user(user_id) if user_id else None
    if user is None or user.role != Role.teacher:
        await message.answer("Преподаватель не найден.", reply_markup=get_cancel_kb())
        return
    await state.update_data(teacher_id=user.id, teacher_name=user.full_name)
    await state.set_state(AdminCreateDeal.waiting_traffer_id)
    await message.answer("ID трафера. Если его нет — отправьте «-».", reply_markup=get_cancel_kb())


@router.message(AdminCreateDeal.waiting_traffer_id)
async def take_traffer(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    traffer_id = None
    traffer_name = "нет"
    if raw not in {"-", "—", "нет", "0", "Нет"}:
        parsed = _parse_id(raw)
        user = await get_user(parsed) if parsed else None
        if user is None or user.role != Role.traffer:
            await message.answer("Трафер не найден. Или отправьте «-».", reply_markup=get_cancel_kb())
            return
        traffer_id = user.id
        traffer_name = user.full_name
    data = await state.get_data()
    course_type = data.get("course_type", "individual")
    if course_type == "group":
        total, traffer_cut, teacher_cut, admin_cut = split_group_bundle(traffer_id is not None)
    else:
        total, traffer_cut, teacher_cut, admin_cut = split_individual(traffer_id is not None)
    await state.update_data(traffer_id=traffer_id)
    await state.set_state(AdminCreateDeal.waiting_amount)
    await message.answer(
        "Проверка суммы\n"
        f"Ученик: {data.get('student_name')}\n"
        f"Преподаватель: {data.get('teacher_name')}\n"
        f"Трафер: {traffer_name}\n"
        f"Сумма {rub(total)}\n"
        f"Трафер {rub(traffer_cut)}\n"
        f"Преподаватель {rub(teacher_cut)}\n"
        f"Админ {rub(admin_cut)}",
        reply_markup=get_confirm_deal_kb(),
    )


@router.callback_query(AdminCreateDeal.waiting_amount, F.data == "deal:confirm")
async def confirm_deal(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    result = await open_deal(
        int(data["student_id"]),
        int(data["teacher_id"]),
        int(data["traffer_id"]) if data.get("traffer_id") else None,
        str(data.get("course_type", "individual")),
    )
    await state.clear()
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(result.text, reply_markup=get_admin_menu())
    if result.ok:
        actor = callback.from_user.id
        for item in result.notices:
            if item.user_id != actor:
                await notify(bot, item.user_id, item.text)


@router.message(F.text == BTN_PAYOUTS)
async def payouts(message: Message, state: FSMContext) -> None:
    await state.clear()
    users = await users_with_balance()
    if not users:
        await message.answer("Никто не ждёт выплату.")
        return
    await message.answer("Кому платим:", reply_markup=get_payouts_kb(users))


@router.callback_query(F.data == "payout:manual")
async def payout_manual(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminPayout.waiting_user_id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer("Введите ID пользователя.", reply_markup=get_cancel_kb())


@router.callback_query(F.data.regexp(r"^payout:\d+$"))
async def payout_pick(callback: CallbackQuery, state: FSMContext) -> None:
    raw = (callback.data or "").split(":", 1)[1]
    user = await get_user(int(raw))
    if user is None:
        await callback.answer("Не найден", show_alert=True)
        return
    await state.set_state(AdminPayout.waiting_amount_to_pay)
    await state.update_data(payout_user_id=user.id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(
            f"{user.full_name}: на балансе {rub(user.balance)}. Какую сумму списать?",
            reply_markup=get_cancel_kb(),
        )


@router.message(AdminPayout.waiting_user_id)
async def payout_user(message: Message, state: FSMContext) -> None:
    user_id = _parse_id(message.text or "")
    user = await get_user(user_id) if user_id else None
    if user is None:
        await message.answer("Пользователь не найден.", reply_markup=get_cancel_kb())
        return
    await state.set_state(AdminPayout.waiting_amount_to_pay)
    await state.update_data(payout_user_id=user.id)
    await message.answer(
        f"{user.full_name}: на балансе {rub(user.balance)}. Какую сумму списать?",
        reply_markup=get_cancel_kb(),
    )


@router.message(AdminPayout.waiting_amount_to_pay)
async def payout_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    try:
        amount = float((message.text or "").replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer("Нужно число.", reply_markup=get_cancel_kb())
        return
    data = await state.get_data()
    result = await payout(int(data["payout_user_id"]), amount)
    if not result.ok:
        await message.answer(result.text, reply_markup=get_cancel_kb())
        return
    await state.clear()
    await message.answer(result.text, reply_markup=get_admin_menu())
    for item in result.notices:
        await notify(bot, item.user_id, item.text)


def _parse_id(raw: str) -> int | None:
    text = raw.strip()
    if not text.isdigit():
        return None
    return int(text)


def _chunks(text: str, size: int = 3500) -> list[str]:
    if len(text) <= size:
        return [text]
    lines = text.split("\n")
    blocks: list[str] = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > size:
            blocks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        blocks.append(current)
    return blocks
