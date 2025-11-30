import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, ADMIN_IDS, logger
from database import Database
from utils import get_main_keyboard

# Импорт роутеров
from handlers import common, booking, tasks, resources, delete_booking, reports, messaging


# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

# Регистрация роутеров
dp.include_router(common.router)
dp.include_router(booking.router)
dp.include_router(tasks.router)
dp.include_router(resources.router)
dp.include_router(delete_booking.router)
dp.include_router(reports.router)
dp.include_router(messaging.router)


async def send_daily_reminders():
    """Ежедневные напоминания о задачах"""
    while True:
        try:
            now = datetime.now()
            if now.hour == 9 and now.minute == 0:
                today = now.strftime('%Y-%m-%d')
                
                to_give = db.get_bookings_for_date(today, 'start')
                to_take = db.get_bookings_for_date(today, 'end')
                
                if to_give or to_take:
                    text = "🔔 <b>НАПОМИНАНИЕ О ЗАДАЧАХ НА СЕГОДНЯ</b>\n\n"
                    
                    if to_give:
                        text += f"🟢 Выдать оборудование: {len(to_give)} шт.\n"
                    
                    if to_take:
                        text += f"🔴 Забрать оборудование: {len(to_take)} шт.\n"
                    
                    text += "\nИспользуйте кнопку 'Сегодня' для просмотра деталей."
                    
                    for admin_id in ADMIN_IDS:
                        try:
                            await bot.send_message(
                                admin_id,
                                text,
                                parse_mode='HTML',
                                reply_markup=get_main_keyboard()
                            )
                        except Exception as e:
                            logger.error(f"Ошибка отправки напоминания админу {admin_id}: {e}")
                
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(60)
        
        except Exception as e:
            logger.error(f"Ошибка в задаче напоминаний: {e}")
            await asyncio.sleep(60)


async def main():
    """Основная функция запуска бота"""
    logger.info("=" * 50)
    logger.info("🚀 Бот запущен")
    logger.info(f"👥 Администраторы: {ADMIN_IDS}")
    logger.info(f"💾 База данных: {db.db_path}")
    logger.info("=" * 50)
    
    # Запуск задачи напоминаний
    asyncio.create_task(send_daily_reminders())
    
    # Запуск polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())