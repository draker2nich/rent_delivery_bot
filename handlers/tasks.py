from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import get_main_keyboard, edit_or_send, format_order
from config import logger

router = Router()
from database import get_database
db = get_database()


@router.callback_query(F.data == "tasks_today")
async def tasks_today(callback: CallbackQuery):
    """Просмотр задач на сегодня"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    orders_to_give = db.get_orders_for_date(today, 'start')
    orders_to_take = db.get_orders_for_date(today, 'end')
    
    if not orders_to_give and not orders_to_take:
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
    
    if orders_to_give:
        text += f"🟢 <b>ВЫДАТЬ ({len(orders_to_give)}):</b>\n"
        for order in orders_to_give[:10]:  # Макс 10
            text += format_order(order, show_items=True)
            text += "\n"
        if len(orders_to_give) > 10:
            text += f"<i>... ещё {len(orders_to_give) - 10}</i>\n"
        text += "\n"
    
    if orders_to_take:
        text += f"🔴 <b>ЗАБРАТЬ ({len(orders_to_take)}):</b>\n"
        for order in orders_to_take[:10]:  # Макс 10
            text += format_order(order, show_items=True)
            text += "\n"
        if len(orders_to_take) > 10:
            text += f"<i>... ещё {len(orders_to_take) - 10}</i>\n"
    
    builder = InlineKeyboardBuilder()
    
    # Кнопки для возврата оборудования
    if orders_to_take:
        for order in orders_to_take[:5]:  # Макс 5 кнопок
            order_id = order[0]
            builder.row(InlineKeyboardButton(
                text=f"✅ Возвращено #{order_id}",
                callback_data=f"complete_{order_id}"
            ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == "tasks_tomorrow")
async def tasks_tomorrow(callback: CallbackQuery):
    """Просмотр задач на завтра"""
    tomorrow = (datetime.now() + timedelta(days=1))
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    orders_to_give = db.get_orders_for_date(tomorrow_str, 'start')
    orders_to_take = db.get_orders_for_date(tomorrow_str, 'end')
    
    if not orders_to_give and not orders_to_take:
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
    
    if orders_to_give:
        text += f"🟢 <b>ВЫДАТЬ ({len(orders_to_give)}):</b>\n"
        for order in orders_to_give[:10]:  # Макс 10
            text += format_order(order, show_items=True)
            text += "\n"
        if len(orders_to_give) > 10:
            text += f"<i>... ещё {len(orders_to_give) - 10}</i>\n"
        text += "\n"
    
    if orders_to_take:
        text += f"🟡 <b>ЗАБРАТЬ ({len(orders_to_take)}):</b>\n"
        for order in orders_to_take[:10]:  # Макс 10
            text += format_order(order, show_items=True)
            text += "\n"
        if len(orders_to_take) > 10:
            text += f"<i>... ещё {len(orders_to_take) - 10}</i>\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("complete_"))
async def complete_order(callback: CallbackQuery):
    """Завершение заказа"""
    order_id = int(callback.data.split("_")[1])
    
    if db.mark_order_completed(order_id):
        await callback.answer(f"✅ Заказ #{order_id} завершён!", show_alert=True)
        logger.info(f"Заказ #{order_id} завершён администратором {callback.from_user.id}")
        
        # Обновляем список задач
        await tasks_today(callback)
    else:
        await callback.answer("❌ Ошибка при завершении заказа", show_alert=True)


@router.callback_query(F.data == "check_week")
async def check_week(callback: CallbackQuery):
    """Просмотр задач на неделю"""
    today = datetime.now()
    week_end = (today + timedelta(days=7)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    orders = db.get_orders_for_period(today_str, week_end)
    
    if not orders:
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
        text += f"📊 Всего заказов: {len(orders)}\n\n"
        
        # Ограничение: показываем максимум 5 заказов
        max_display = 5
        for i, order in enumerate(orders[:max_display]):
            text += format_order(order, show_items=True)
            if i < min(len(orders), max_display) - 1:
                text += "━━━━━━━━━━━━━━━━\n\n"
        
        if len(orders) > max_display:
            text += f"\n<i>... и ещё {len(orders) - max_display} заказов</i>\n"
            text += f"<i>Используйте 'Календарь' для полного просмотра</i>"
        
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
    
    orders = db.get_orders_for_period(today_str, month_end)
    
    if not orders:
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
        text += f"📋 Всего заказов: {len(orders)}\n\n"
        
        # Ограничение: показываем максимум 5 заказов
        max_display = 5
        for i, order in enumerate(orders[:max_display]):
            text += format_order(order, show_items=True)
            if i < min(len(orders), max_display) - 1:
                text += "━━━━━━━━━━━━━━━━\n\n"
        
        if len(orders) > max_display:
            text += f"\n<i>Показано {max_display} из {len(orders)} заказов</i>\n"
            text += f"<i>Используйте 'Отчёты' для полного списка</i>"
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
        
        await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    
    await callback.answer()