import asyncio
import signal
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, ADMIN_IDS, logger
from database import get_database  # ИЗМЕНЕНО
from utils import get_main_keyboard

# Импорт роутеров
from handlers import (
    common, 
    booking, 
    tasks, 
    resources, 
    delete_booking, 
    reports, 
    messaging
)

# Импорт новых модулей
from handlers import edit_resource, edit_booking, broadcast, calendar as calendar_handler


# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = get_database()  # ИЗМЕНЕНО - используем singleton

# Регистрация роутеров (порядок важен!)
dp.include_router(common.router)
dp.include_router(booking.router)
dp.include_router(tasks.router)
dp.include_router(resources.router)
dp.include_router(edit_resource.router)
dp.include_router(edit_booking.router)
dp.include_router(delete_booking.router)
dp.include_router(reports.router)
dp.include_router(messaging.router)
dp.include_router(broadcast.router)
dp.include_router(calendar_handler.router)

# Флаг для остановки задач
shutdown_event = asyncio.Event()


async def send_daily_reminders():
    """Ежедневные напоминания о задачах"""
    while not shutdown_event.is_set():
        try:
            now = datetime.now()
            if now.hour == 9 and now.minute == 0:
                today = now.strftime('%Y-%m-%d')
                
                # Используем новый API
                orders_to_give = db.get_orders_for_date(today, 'start')
                orders_to_take = db.get_orders_for_date(today, 'end')
                
                if orders_to_give or orders_to_take:
                    text = "🔔 <b>НАПОМИНАНИЕ О ЗАДАЧАХ НА СЕГОДНЯ</b>\n\n"
                    
                    if orders_to_give:
                        text += f"🟢 Выдать оборудование: {len(orders_to_give)} заказов\n"
                    
                    if orders_to_take:
                        text += f"🔴 Забрать оборудование: {len(orders_to_take)} заказов\n"
                    
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
                
                await asyncio.sleep(3600)  # Ждем час
            else:
                await asyncio.sleep(60)  # Проверяем каждую минуту
        
        except asyncio.CancelledError:
            logger.info("Задача напоминаний отменена")
            break
        except Exception as e:
            logger.error(f"Ошибка в задаче напоминаний: {e}")
            await asyncio.sleep(60)


async def on_shutdown():
    """Корректное завершение работы бота"""
    logger.info("🛑 Остановка бота...")
    
    # Останавливаем задачу напоминаний
    shutdown_event.set()
    
    # Закрываем сессию бота
    await bot.session.close()
    
    logger.info("✅ Бот остановлен")


async def main():
    """Основная функция запуска бота"""
    logger.info("=" * 50)
    logger.info("🚀 Бот запущен")
    logger.info(f"👥 Администраторы: {ADMIN_IDS}")
    logger.info(f"💾 База данных: {db.db_path}")
    logger.info("=" * 50)
    
    # Запуск задачи напоминаний
    reminder_task = asyncio.create_task(send_daily_reminders())
    
    try:
        # Запуск polling
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки")
    finally:
        # Корректное завершение
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем")