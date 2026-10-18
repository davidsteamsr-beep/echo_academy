from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from bot.database import deals_for_student, list_courses, mock_payment, open_invoice, open_leads, rub
from bot.filters import IsStudent
from bot.handlers.common import notify
from bot.keyboards import BTN_COURSES, BTN_PAY, get_courses_kb, get_pay_kb

router = Router()
router.message.filter(IsStudent())
router.callback_query.filter(IsStudent())


@router.message(F.text == BTN_COURSES)
async def courses(message: Message) -> None:
    if message.from_user is None:
        return
    rows = await deals_for_student(message.from_user.id)
    if not rows:
        await message.answer("Оплаченных курсов нет.")
        return
    lines = [f"#{deal.id} · {title} · {rub(deal.total_amount)}" for deal, title in rows]
    await message.answer("Мои курсы:\n" + "\n".join(lines))


@router.message(F.text == BTN_PAY)
async def pay_menu(message: Message) -> None:
    if message.from_user is None:
        return
    opened = await open_leads(message.from_user.id)
    courses_all = await list_courses()
    if opened:
        items = [(lead.id, f"Оплатить · {course.title} · {rub(course.base_price)}") for lead, course in opened]
        await message.answer("Открытые счета:", reply_markup=get_pay_kb(items))
    await message.answer("Направления:", reply_markup=get_courses_kb(courses_all))


@router.callback_query(F.data.startswith("buy:"))
async def buy(callback: CallbackQuery) -> None:
    course_id = int(callback.data.split(":", 1)[1]) if callback.data else 0
    result = await open_invoice(callback.from_user.id, course_id)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer(result.text)


@router.callback_query(F.data.startswith("pay:"))
async def pay(callback: CallbackQuery, bot: Bot) -> None:
    lead_id = int(callback.data.split(":", 1)[1]) if callback.data else 0
    result = await mock_payment(lead_id)
    await callback.answer("Готово" if result.ok else "Не вышло", show_alert=not result.ok)
    if isinstance(callback.message, Message):
        await callback.message.answer(result.text)
    if result.ok:
        for item in result.notices:
            if item.user_id != callback.from_user.id:
                await notify(bot, item.user_id, item.text)
