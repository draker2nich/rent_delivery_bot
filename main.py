import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, ADMIN_IDS, DATABASE_PATH, logger
from background_tasks import send_daily_reminders

# Прямые импорты обработчиков
from handlers.handler_common import router as common_router
from handlers.handler_booking import router as booking_router
from handlers.handler_tasks import router as tasks_router
from handlers.handler_resources import router as resources_router
from handlers.handler_delete_booking import router as delete_booking_router
from handlers.handler_reports import router as reports_router
from handlers.handler_messages import router as messages_router


async def main():
    """Основная функция запуска бота"""
    logger.info("=" * 50)
    logger.info("🚀 Бот запущен")
    logger.info(f"👥 Администраторы: {ADMIN_IDS}")
    logger.info(f"💾 База данных: {DATABASE_PATH}")
    logger.info("=" * 50)
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация всех роутеров
    dp.include_router(common_router)
    dp.include_router(booking_router)
    dp.include_router(tasks_router)
    dp.include_router(resources_router)
    dp.include_router(delete_booking_router)
    dp.include_router(reports_router)
    dp.include_router(messages_router)
    
    # Запуск фоновых задач
    asyncio.create_task(send_daily_reminders(bot))
    
    # Запуск polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())