import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message

from bot.database import get_user
from bot.keyboards import BTN_CANCEL, get_main_menu
from bot.states import AdminCreateDeal, AdminPayout

logger = logging.getLogger(__name__)
router = Router()
fallback_router = Router()


async def notify(bot: Bot, user_id: int, text: str) -> None:
    try:
        await bot.send_message(user_id, text)
    except Exception:
        logger.info("Не удалось написать %s", user_id)


def setup_errors(dp: Dispatcher) -> None:
    @dp.error()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception("Сбой обработчика", exc_info=event.exception)
        message = event.update.message if event.update else None
        if message is None and event.update and event.update.callback_query:
            maybe = event.update.callback_query.message
            if isinstance(maybe, Message):
                message = maybe
        if message is not None:
            try:
                await message.answer("Не вышло обработать запрос. Попробуйте ещё раз.")
            except Exception:
                logger.info("Не удалось сообщить об ошибке")


@router.message(StateFilter(AdminCreateDeal, AdminPayout), F.text.casefold() == BTN_CANCEL.casefold())
@router.message(StateFilter(AdminCreateDeal, AdminPayout), F.text.casefold() == "отмена")
async def cancel_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(message.from_user.id) if message.from_user else None
    role = user.role.value if user else "student"
    await message.answer("Отменено.", reply_markup=get_main_menu(role))


@router.callback_query(F.data == "cancel")
async def cancel_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    user = await get_user(callback.from_user.id)
    role = user.role.value if user else "student"
    if isinstance(callback.message, Message):
        await callback.message.answer("Отменено.", reply_markup=get_main_menu(role))


@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    user = await get_user(callback.from_user.id)
    role = user.role.value if user else "student"
    if isinstance(callback.message, Message):
        await callback.message.answer("Главное меню.", reply_markup=get_main_menu(role))


@fallback_router.message()
async def fallback(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    if await state.get_state():
        await message.answer("Жду ответ по текущему шагу или нажмите «Отмена».")
        return
    if message.text.startswith("/"):
        await message.answer("Неизвестная команда. Нажмите /start.")
        return
    await message.answer("Используйте кнопки меню или /start.")
