import asyncio
import signal
import shutil
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, ADMIN_IDS, logger
from database import get_database
from utils import get_main_keyboard
from middleware import AdminCheckMiddleware  # НОВОЕ

# Импорт роутеров
from handlers import (
    common, 
    booking, 
    tasks, 
    resources, 
    delete_booking, 
    reports, 
    messaging,
    edit_resource, 
    edit_booking, 
    broadcast, 
    calendar as calendar_handler
)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = get_database()

# РЕГИСТРАЦИЯ MIDDLEWARE
dp.message.middleware(AdminCheckMiddleware())
dp.callback_query.middleware(AdminCheckMiddleware())

# Регистрация роутеров
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
    """Ежедневные напоминания о задачах и просроченных заказах"""
    while not shutdown_event.is_set():
        try:
            now = datetime.now()
            
            # Отправка напоминаний в 9:00
            if now.hour == 9 and now.minute == 0:
                today = now.strftime('%Y-%m-%d')
                
                # Обновляем статусы просроченных
                db.update_overdue_status()
                
                # Получаем данные
                orders_to_give = db.get_orders_to_give_today()
                orders_to_return = db.get_orders_to_return_today()
                overdue_orders = db.get_overdue_orders()
                
                # Формируем сообщение только если есть задачи
                if orders_to_give or orders_to_return or overdue_orders:
                    text = "🔔 <b>НАПОМИНАНИЕ О ЗАДАЧАХ НА СЕГОДНЯ</b>\n\n"
                    
                    if overdue_orders:
                        text += f"🔴 Просроченных возвратов: {len(overdue_orders)}\n"
                        for order in overdue_orders[:3]:
                            order_id = order[0]
                            client_name = order[1]
                            days = int(order[9]) if len(order) > 9 else 0
                            text += f"   • Заказ #{order_id} ({client_name}) — {days} дн.\n"
                        text += "\n"
                    
                    if orders_to_give:
                        text += f"🟢 Выдать оборудование: {len(orders_to_give)} заказов\n"
                    
                    if orders_to_return:
                        text += f"🔴 Забрать оборудование: {len(orders_to_return)} заказов\n"
                    
                    text += "\n📱 Используйте кнопку 'Сегодня' для просмотра деталей."
                    
                    # Отправляем всем администраторам
                    for admin_id in ADMIN_IDS:
                        try:
                            await bot.send_message(
                                admin_id,
                                text,
                                parse_mode='HTML',
                                reply_markup=get_main_keyboard()
                            )
                            logger.info(f"Напоминание отправлено админу {admin_id}")
                        except Exception as e:
                            logger.error(f"Ошибка отправки напоминания админу {admin_id}: {e}")
                
                # Ждём час перед следующей проверкой
                await asyncio.sleep(3600)
            else:
                # Проверяем каждую минуту
                await asyncio.sleep(60)
        
        except asyncio.CancelledError:
            logger.info("Задача напоминаний остановлена")
            break
        except Exception as e:
            logger.error(f"Ошибка в задаче напоминаний: {e}")
            await asyncio.sleep(60)


async def backup_database():
    """Ежедневное резервное копирование базы данных"""
    while not shutdown_event.is_set():
        try:
            now = datetime.now()
            
            # Backup в 3:00 ночи
            if now.hour == 3 and now.minute == 0:
                backup_dir = "backups"
                
                # Создаём папку для бэкапов если её нет
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                    logger.info(f"Создана папка для бэкапов: {backup_dir}")
                
                # Имя файла с датой
                backup_name = f"booking_backup_{now.strftime('%Y%m%d')}.db"
                backup_path = os.path.join(backup_dir, backup_name)
                
                # Копируем базу данных
                shutil.copy2(db.db_path, backup_path)
                logger.info(f"✅ Создан бэкап: {backup_path}")
                
                # Удаляем старые бэкапы (старше 30 дней)
                for filename in os.listdir(backup_dir):
                    file_path = os.path.join(backup_dir, filename)
                    if os.path.isfile(file_path):
                        file_age_days = (now - datetime.fromtimestamp(
                            os.path.getmtime(file_path)
                        )).days
                        
                        if file_age_days > 30:
                            os.remove(file_path)
                            logger.info(f"Удалён старый бэкап: {filename}")
                
                await asyncio.sleep(3600)  # Ждём час
            else:
                await asyncio.sleep(60)  # Проверяем каждую минуту
        
        except asyncio.CancelledError:
            logger.info("Задача backup остановлена")
            break
        except Exception as e:
            logger.error(f"Ошибка backup: {e}")
            await asyncio.sleep(60)


async def on_shutdown():
    """Корректное завершение работы бота"""
    logger.info("🛑 Остановка бота...")
    
    # Останавливаем задачи
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
    
    # Запуск задач
    reminder_task = asyncio.create_task(send_daily_reminders())
    backup_task = asyncio.create_task(backup_database())
    
    try:
        # Запуск polling
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки")
    finally:
        # Корректное завершение
        reminder_task.cancel()
        backup_task.cancel()
        
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        
        try:
            await backup_task
        except asyncio.CancelledError:
            pass
        
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем")