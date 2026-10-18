from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.database import admin_ids, get_user, rub, traffer_stats
from bot.filters import IsTraffer
from bot.handlers.common import notify
from bot.keyboards import BTN_BALANCE, BTN_LINK, BTN_STATS

router = Router()
router.message.filter(IsTraffer())


@router.message(F.text == BTN_LINK)
async def my_link(message: Message, bot: Bot) -> None:
    user = await get_user(message.from_user.id) if message.from_user else None
    if user is None:
        await message.answer("Сначала /start.")
        return
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.ref_code}"
    await message.answer(f"Ваша ссылка:\n{link}")


@router.message(F.text == BTN_STATS)
async def stats(message: Message) -> None:
    if message.from_user is None:
        return
    paid, total = await traffer_stats(message.from_user.id)
    rate = round(100 * paid / total) if total else 0
    await message.answer(f"Оплачено {paid} из {total}. Конверсия {rate}%.")


@router.message(F.text == BTN_BALANCE)
async def balance(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return
    user = await get_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала /start.")
        return
    ids = await admin_ids()
    if user.balance <= 0:
        await message.answer(f"Баланс {rub(0)}. Выводить нечего.")
        return
    if not ids:
        await message.answer(f"Баланс {rub(user.balance)}. Админ ещё не назначен, запрос некому отправить.")
        return
    text = f"Запрос на вывод\n{user.full_name}\nid {user.id}\n{rub(user.balance)}"
    for admin_id in ids:
        await notify(bot, admin_id, text)
    await message.answer(f"Баланс {rub(user.balance)}. Запрос на вывод отправлен админу.")
