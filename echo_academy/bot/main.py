import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import (
    BOT_MODE,
    BOT_TOKEN,
    PORT,
    WEBHOOK_HOST,
    WEBHOOK_PATH,
    WEBHOOK_SECRET,
)
from bot.database import init_db
from bot.handlers import admin, common, start, student, teacher, traffer

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    common.setup_errors(dp)
    dp.include_routers(
        common.router,
        start.router,
        admin.router,
        teacher.router,
        traffer.router,
        student.router,
        common.fallback_router,
    )
    return dp


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Starting polling mode")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook(bot: Bot, dp: Dispatcher) -> None:
    if not WEBHOOK_HOST:
        raise SystemExit("BOT_MODE=webhook requires WEBHOOK_HOST (e.g. https://your-app.onrender.com)")

    webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    logger.info("Starting webhook mode → %s", webhook_url)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET or None,
    ).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    await bot.set_webhook(
        url=webhook_url,
        secret_token=WEBHOOK_SECRET or None,
        drop_pending_updates=True,
    )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info("HTTP server on 0.0.0.0:%s", PORT)

    # Keep process alive
    await asyncio.Event().wait()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if not BOT_TOKEN:
        raise SystemExit("Укажите BOT_TOKEN в .env (или в Environment Variables на Render)")

    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = build_dispatcher()

    if BOT_MODE == "webhook":
        await run_webhook(bot, dp)
    else:
        await run_polling(bot, dp)


if __name__ == "__main__":
    asyncio.run(main())
