from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from bot.database import Role, create_referral_lead, first_course, get_user_by_ref, touch_user
from bot.keyboards import get_main_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message, command: CommandObject) -> None:
    tg = message.from_user
    if tg is None:
        return
    user, created = await touch_user(tg.id, tg.username, tg.full_name)
    if not user.is_active:
        await message.answer("Кабинет заморожен.")
        return
    extra = ""
    payload = command.args or ""
    if created and payload.startswith("ref_"):
        code = payload[4:]
        traffer = await get_user_by_ref(code)
        if traffer is None or traffer.id == user.id or traffer.role != Role.traffer:
            extra = "\nРеферальный код не сработал."
        else:
            lead = await create_referral_lead(user.id, traffer.id)
            course = await first_course()
            title = course.title if course else "курс"
            if lead:
                extra = (
                    f"\nВас привёл {traffer.full_name}. "
                    f"Заявка #{lead.id} на «{title}», статус new."
                )
    await message.answer(
        f"ECHO Academy\n{user.full_name}, кабинет: {user.role.value}.{extra}",
        reply_markup=get_main_menu(user.role.value),
    )
