import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def handle_health_check(request):
    """Render port tekshiruvi (healthcheck) uchun mini HTTP handler."""
    return web.Response(text="OpenBudget Telegram Bot ishlamoqda (OK)", status=200)

async def start_health_check_server():
    """Render Web Service talab qiladigan HTTP portni ochish."""
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Render HTTP Health Check server {port}-portda ishga tushdi.")

async def main():
    if not BOT_TOKEN:
        logger.error("XATO: BOT_TOKEN o'rnatilmagan! Environment Variables yoki .env faylida BOT_TOKEN ni ko'rsating.")
        return

    # Render Web Service port detector uchun HTTP serverni orqa fonda ishga tushirish
    try:
        await start_health_check_server()
    except Exception as e:
        logger.warning(f"HTTP serverni ishga tushirishda ogohlantirish: {e}")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("OpenBudget Ovoz Yig'ish Boti ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
