import asyncio
from datetime import datetime
from aiogram import Bot

from database import Database
from utils import get_main_keyboard
from config import ADMIN_IDS, logger

db = Database()


async def send_daily_reminders(bot: Bot):
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