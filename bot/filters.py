from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from bot.config import ADMIN_ID
from bot.database import Role, get_user


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        if ADMIN_ID and user.id == ADMIN_ID:
            return True
        db_user = await get_user(user.id)
        return bool(db_user and db_user.role == Role.admin)


class IsTraffer(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        return await _has_role(event, Role.traffer)


class IsTeacher(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        return await _has_role(event, Role.teacher)


class IsStudent(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        return await _has_role(event, Role.student)


async def _has_role(event: TelegramObject, role: Role) -> bool:
    user = getattr(event, "from_user", None)
    if user is None:
        return False
    db_user = await get_user(user.id)
    return bool(db_user and db_user.role == role)
