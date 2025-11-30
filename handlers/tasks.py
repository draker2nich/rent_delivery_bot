from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from utils import get_main_keyboard, edit_or_send, format_booking
from config import logger

router = Router()
db = Database()


@router.callback_query(F.data == "tasks_today")
async def tasks_today(callback: CallbackQuery):
    """Просмотр задач на сегодня"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    to_give = db.get_bookings_for_date(today, 'start')
    to_take = db.get_bookings_for_date(today, 'end')
    
    if not to_give and not to_take:
        await edit_or_send(
            callback,
            "📅 <b>Задачи на сегодня</b>\n\n"
            "✅ На сегодня задач нет.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await callback.answer()
        return
    
    text = f"📅 <b>ЗАДАЧИ НА СЕГОДНЯ</b>\n"
    text += f"📆 {datetime.now().strftime('%d.%m.%Y')}\n\n"
    
    if to_give:
        text += f"🟢 <b>ВЫДАТЬ ОБОРУДОВАНИЕ ({len(to_give)}):</b>\n\n"
        for booking in to_give:
            text += format_booking(booking)
            text += "━━━━━━━━━━━━━━━━\n\n"
    
    if to_take:
        text += f"🔴 <b>ЗАБРАТЬ ОБОРУДОВАНИЕ ({len(to_take)}):</b>\n\n"
        for i, booking in enumerate(to_take):
            text += format_booking(booking)
            if i < len(to_take) - 1:
                text += "━━━━━━━━━━━━━━━━\n\n"
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки для возврата оборудования
    if to_take:
        for booking in to_take:
            builder.row(InlineKeyboardButton(
                text=f"✅ Возвращено #{booking[0]}",
                callback_data=f"complete_{booking[0]}"
            ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == "tasks_tomorrow")
async def tasks_tomorrow(callback: CallbackQuery):
    """Просмотр задач на завтра"""
    tomorrow = (datetime.now() + timedelta(days=1))
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    to_give = db.get_bookings_for_date(tomorrow_str, 'start')
    to_take = db.get_bookings_for_date(tomorrow_str, 'end')
    
    if not to_give and not to_take:
        await edit_or_send(
            callback,
            "📅 <b>Задачи на завтра</b>\n\n"
            "✅ На завтра задач нет.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await callback.answer()
        return
    
    text = f"📅 <b>ЗАДАЧИ НА ЗАВТРА</b>\n"
    text += f"📆 {tomorrow.strftime('%d.%m.%Y')}\n\n"
    
    if to_give:
        text += f"🟢 <b>ВЫДАТЬ ОБОРУДОВАНИЕ ({len(to_give)}):</b>\n\n"
        for booking in to_give:
            text += format_booking(booking)
            text += "━━━━━━━━━━━━━━━━\n\n"
    
    if to_take:
        text += f"🟡 <b>ЗАБРАТЬ ОБОРУДОВАНИЕ ({len(to_take)}):</b>\n\n"
        for i, booking in enumerate(to_take):
            text += format_booking(booking)
            if i < len(to_take) - 1:
                text += "━━━━━━━━━━━━━━━━\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("complete_"))
async def complete_booking(callback: CallbackQuery):
    """Завершение бронирования"""
    booking_id = int(callback.data.split("_")[1])
    
    if db.mark_booking_completed(booking_id):
        await callback.answer(f"✅ Бронь #{booking_id} завершена!", show_alert=True)
        logger.info(f"Бронь #{booking_id} завершена администратором {callback.from_user.id}")
        
        # Обновляем список задач
        await tasks_today(callback)
    else:
        await callback.answer("❌ Ошибка при завершении брони", show_alert=True)


@router.callback_query(F.data == "check_week")
async def check_week(callback: CallbackQuery):
    """Просмотр задач на неделю"""
    today = datetime.now()
    week_end = (today + timedelta(days=7)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    bookings = db.get_bookings_for_period(today_str, week_end)
    
    if not bookings:
        await edit_or_send(
            callback,
            "📅 <b>Записи на неделю</b>\n\n"
            "✅ На неделю вперёд нет записей.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        text = f"📅 <b>ЗАПИСИ НА НЕДЕЛЮ</b>\n"
        text += f"📆 {today.strftime('%d.%m.%Y')} - {(today + timedelta(days=7)).strftime('%d.%m.%Y')}\n"
        text += f"📊 Всего: {len(bookings)}\n\n"
        
        for i, booking in enumerate(bookings):
            text += format_booking(booking)
            if i < len(bookings) - 1:
                text += "━━━━━━━━━━━━━━━━\n\n"
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
        
        await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    
    await callback.answer()


@router.callback_query(F.data == "view_calendar")
async def view_calendar(callback: CallbackQuery):
    """Просмотр календаря на месяц"""
    today = datetime.now()
    month_end = (today + timedelta(days=30)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    bookings = db.get_bookings_for_period(today_str, month_end)
    
    if not bookings:
        await edit_or_send(
            callback,
            "📊 <b>Календарь на месяц</b>\n\n"
            "✅ На ближайший месяц нет записей.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        text = f"📊 <b>КАЛЕНДАРЬ НА МЕСЯЦ</b>\n"
        text += f"📆 {today.strftime('%d.%m.%Y')} - {(today + timedelta(days=30)).strftime('%d.%m.%Y')}\n"
        text += f"📋 Всего: {len(bookings)}\n\n"
        
        for i, booking in enumerate(bookings[:15]):
            text += format_booking(booking)
            if i < min(len(bookings), 15) - 1:
                text += "━━━━━━━━━━━━━━━━\n\n"
        
        if len(bookings) > 15:
            text += f"\n... и ещё {len(bookings) - 15} записей"
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
        
        await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    
    await callback.answer()