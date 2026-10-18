from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.database import admin_ids, deals_for_teacher, get_user, rub
from bot.filters import IsTeacher
from bot.handlers.common import notify
from bot.keyboards import BTN_BALANCE, BTN_STUDENTS

router = Router()
router.message.filter(IsTeacher())


@router.message(F.text == BTN_STUDENTS)
async def students(message: Message) -> None:
    if message.from_user is None:
        return
    rows = await deals_for_teacher(message.from_user.id)
    if not rows:
        await message.answer("Учеников пока нет.")
        return
    lines = [f"#{deal.id} · {title} · вам {rub(deal.teacher_cut)} · {deal.payout_status.value}" for deal, title in rows]
    await message.answer("Ученики:\n" + "\n".join(lines))


@router.message(F.text == BTN_BALANCE)
async def balance(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return
    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала /start.")
        return
    if user.balance <= 0:
        await message.answer(f"Баланс {rub(0)}.")
        return
    ids = await admin_ids()
    text = f"Запрос на вывод\n{user.full_name}\nid {user.id}\n{rub(user.balance)}"
    for admin_id in ids:
        await notify(bot, admin_id, text)
    note = " Запрос отправлен админу." if ids else " Админ ещё не назначен."
    await message.answer(f"Баланс {rub(user.balance)}.{note}")
