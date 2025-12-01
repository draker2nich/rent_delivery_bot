from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import get_main_keyboard, edit_or_send, format_order
from config import logger
from database import get_database

router = Router()
db = get_database()


@router.callback_query(F.data == "tasks_today")
async def tasks_today(callback: CallbackQuery):
    """Задачи на сегодня: выдать и забрать оборудование"""
    
    # Обновляем статусы просроченных заказов
    db.update_overdue_status()
    
    # Получаем данные
    orders_to_give = db.get_orders_to_give_today()
    orders_to_return = db.get_orders_to_return_today()
    overdue_orders = db.get_overdue_orders()
    
    today_str = datetime.now().strftime('%d.%m.%Y, %A')
    
    # Формируем сообщение
    text = f"📅 <b>ЗАДАЧИ НА СЕГОДНЯ</b>\n"
    text += f"📆 {today_str}\n\n"
    
    # БЛОК 1: Просроченные возвраты (если есть)
    if overdue_orders:
        text += f"🔴 <b>ПРОСРОЧЕНО ({len(overdue_orders)}):</b>\n"
        text += "⚠️ <i>Оборудование не возвращено вовремя!</i>\n\n"
        
        for order in overdue_orders[:5]:  # Макс 5
            order_id = order[0]
            client_name = order[1]
            client_phone = order[2]
            end_date = order[4]
            days_overdue = int(order[9]) if len(order) > 9 else 0
            
            text += f"🔴 <b>#{order_id}</b> — ПРОСРОЧЕНО {days_overdue} дн.\n"
            text += f"   👤 {client_name} | 📞 {client_phone}\n"
            text += f"   📅 Должен был вернуть: {end_date}\n"
            
            # Получаем позиции
            items = db.get_order_items(order_id)
            if items:
                items_text = ", ".join([f"{name}×{qty}" for _, name, qty, _ in items])
                text += f"   📦 {items_text}\n"
            
            text += "\n"
        
        if len(overdue_orders) > 5:
            text += f"<i>... и ещё {len(overdue_orders) - 5} просроченных</i>\n"
        
        text += "━━━━━━━━━━━━━━━━\n\n"
    
    # БЛОК 2: Выдать сегодня
    if orders_to_give:
        text += f"🟢 <b>ВЫДАТЬ СЕГОДНЯ ({len(orders_to_give)}):</b>\n\n"
        
        for order in orders_to_give[:5]:  # Макс 5
            order_id = order[0]
            client_name = order[1]
            client_phone = order[2]
            start_date = order[3]
            end_date = order[4]
            delivery_type = order[5]
            delivery_comment = order[6]
            cost = order[7]
            
            delivery_emoji = "🚗" if delivery_type == 'delivery' else "🏃"
            delivery_text = "Доставка" if delivery_type == 'delivery' else "Самовывоз"
            
            text += f"🟢 <b>#{order_id}</b> — К ВЫДАЧЕ\n"
            text += f"   👤 {client_name} | 📞 {client_phone}\n"
            text += f"   📅 {start_date} — {end_date}\n"
            
            # Получаем позиции
            items = db.get_order_items(order_id)
            if items:
                items_text = ", ".join([f"{name}×{qty}" for _, name, qty, _ in items])
                text += f"   📦 {items_text}\n"
            
            text += f"   {delivery_emoji} {delivery_text}"
            if delivery_comment:
                short_comment = delivery_comment[:40] + "..." if len(delivery_comment) > 40 else delivery_comment
                text += f" | 💬 {short_comment}"
            
            if cost:
                text += f"\n   💰 {cost}"
            
            text += "\n\n"
        
        if len(orders_to_give) > 5:
            text += f"<i>... и ещё {len(orders_to_give) - 5} к выдаче</i>\n"
        
        text += "━━━━━━━━━━━━━━━━\n\n"
    else:
        text += "🟢 <b>ВЫДАТЬ СЕГОДНЯ:</b>\n"
        text += "   ✅ Нет задач\n\n"
    
    # БЛОК 3: Забрать сегодня
    if orders_to_return:
        text += f"🔴 <b>ЗАБРАТЬ СЕГОДНЯ ({len(orders_to_return)}):</b>\n\n"
        
        for order in orders_to_return[:5]:  # Макс 5
            order_id = order[0]
            client_name = order[1]
            client_phone = order[2]
            start_date = order[3]
            end_date = order[4]
            
            text += f"🔴 <b>#{order_id}</b> — ЗАБРАТЬ СЕГОДНЯ\n"
            text += f"   👤 {client_name} | 📞 {client_phone}\n"
            text += f"   📅 Период: {start_date} — {end_date}\n"
            
            # Получаем позиции
            items = db.get_order_items(order_id)
            if items:
                items_text = ", ".join([f"{name}×{qty}" for _, name, qty, _ in items])
                text += f"   📦 {items_text}\n"
            
            text += "\n"
        
        if len(orders_to_return) > 5:
            text += f"<i>... и ещё {len(orders_to_return) - 5} к возврату</i>\n"
    else:
        text += "🔴 <b>ЗАБРАТЬ СЕГОДНЯ:</b>\n"
        text += "   ✅ Нет задач\n"
    
    # Формируем кнопки
    builder = InlineKeyboardBuilder()
    
    # Кнопки выдачи оборудования (для заказов со статусом pending)
    if orders_to_give:
        text += "\n\n<i>Кнопки для подтверждения выдачи:</i>"
        
        for order in orders_to_give[:5]:  # Макс 5 кнопок
            order_id = order[0]
            client_name = order[1]
            builder.row(InlineKeyboardButton(
                text=f"✅ Выдано #{order_id} ({client_name})",
                callback_data=f"issue_order_{order_id}"
            ))
    
    # Кнопки подтверждения возврата (для заказов со статусом issued)
    if orders_to_return:
        if orders_to_give:
            text += "\n\n<i>Кнопки для подтверждения возврата:</i>"
        else:
            text += "\n\n<i>Используйте кнопки ниже для подтверждения возврата:</i>"
        
        for order in orders_to_return[:5]:  # Макс 5 кнопок
            order_id = order[0]
            client_name = order[1]
            builder.row(InlineKeyboardButton(
                text=f"✅ Возврат #{order_id} ({client_name})",
                callback_data=f"confirm_return_{order_id}"
            ))
    
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="tasks_today"))
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main"))
    
    await edit_or_send(
        callback, 
        text, 
        reply_markup=builder.as_markup(), 
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "tasks_tomorrow")
async def tasks_tomorrow(callback: CallbackQuery):
    """Задачи на завтра: выдать и забрать оборудование"""
    
    orders_to_give = db.get_orders_to_give_tomorrow()
    orders_to_return = db.get_orders_to_return_tomorrow()
    
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%d.%m.%Y, %A')
    
    text = f"📅 <b>ЗАДАЧИ НА ЗАВТРА</b>\n"
    text += f"📆 {tomorrow_str}\n\n"
    
    # БЛОК 1: Выдать завтра
    if orders_to_give:
        text += f"🟢 <b>ВЫДАТЬ ЗАВТРА ({len(orders_to_give)}):</b>\n\n"
        
        for order in orders_to_give[:5]:
            order_id = order[0]
            client_name = order[1]
            client_phone = order[2]
            start_date = order[3]
            end_date = order[4]
            delivery_type = order[5]
            delivery_comment = order[6]
            
            delivery_emoji = "🚗" if delivery_type == 'delivery' else "🏃"
            delivery_text = "Доставка" if delivery_type == 'delivery' else "Самовывоз"
            
            text += f"🟢 <b>#{order_id}</b>\n"
            text += f"   👤 {client_name} | 📞 {client_phone}\n"
            text += f"   📅 {start_date} — {end_date}\n"
            
            items = db.get_order_items(order_id)
            if items:
                items_text = ", ".join([f"{name}×{qty}" for _, name, qty, _ in items])
                text += f"   📦 {items_text}\n"
            
            text += f"   {delivery_emoji} {delivery_text}"
            if delivery_comment:
                short_comment = delivery_comment[:40] + "..." if len(delivery_comment) > 40 else delivery_comment
                text += f" | 💬 {short_comment}"
            
            text += "\n\n"
        
        if len(orders_to_give) > 5:
            text += f"<i>... и ещё {len(orders_to_give) - 5}</i>\n"
        
        text += "━━━━━━━━━━━━━━━━\n\n"
    else:
        text += "🟢 <b>ВЫДАТЬ ЗАВТРА:</b>\n"
        text += "   ✅ Нет задач\n\n"
    
    # БЛОК 2: Забрать завтра
    if orders_to_return:
        text += f"🟡 <b>ЗАБРАТЬ ЗАВТРА ({len(orders_to_return)}):</b>\n\n"
        
        for order in orders_to_return[:5]:
            order_id = order[0]
            client_name = order[1]
            client_phone = order[2]
            start_date = order[3]
            end_date = order[4]
            
            text += f"🟡 <b>#{order_id}</b>\n"
            text += f"   👤 {client_name} | 📞 {client_phone}\n"
            text += f"   📅 {start_date} — {end_date}\n"
            
            items = db.get_order_items(order_id)
            if items:
                items_text = ", ".join([f"{name}×{qty}" for _, name, qty, _ in items])
                text += f"   📦 {items_text}\n"
            
            text += "\n"
        
        if len(orders_to_return) > 5:
            text += f"<i>... и ещё {len(orders_to_return) - 5}</i>\n"
    else:
        text += "🟡 <b>ЗАБРАТЬ ЗАВТРА:</b>\n"
        text += "   ✅ Нет задач\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        text,
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("issue_order_"))
async def issue_order_handler(callback: CallbackQuery):
    """Обработчик выдачи оборудования клиенту"""
    order_id = int(callback.data.split("_")[2])
    
    # Выдаём оборудование
    success = db.issue_order(order_id, callback.from_user.id)
    
    if success:
        await callback.answer(
            f"✅ Оборудование по заказу #{order_id} выдано клиенту!",
            show_alert=True
        )
        logger.info(
            f"Администратор {callback.from_user.id} выдал "
            f"оборудование по заказу #{order_id}"
        )
        
        # Обновляем список задач
        await tasks_today(callback)
    else:
        await callback.answer(
            f"❌ Ошибка выдачи оборудования для заказа #{order_id}",
            show_alert=True
        )


@router.callback_query(F.data.startswith("confirm_return_"))
async def confirm_return_handler(callback: CallbackQuery):
    """Обработчик подтверждения возврата оборудования"""
    order_id = int(callback.data.split("_")[2])
    
    # Подтверждаем возврат
    success = db.confirm_return(order_id, callback.from_user.id)
    
    if success:
        await callback.answer(
            f"✅ Возврат оборудования по заказу #{order_id} подтверждён!",
            show_alert=True
        )
        logger.info(
            f"Администратор {callback.from_user.id} подтвердил "
            f"возврат заказа #{order_id}"
        )
        
        # Обновляем список задач
        await tasks_today(callback)
    else:
        await callback.answer(
            f"❌ Ошибка подтверждения возврата для заказа #{order_id}",
            show_alert=True
        )


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
        await callback.answer()
        return
    
    text = f"📅 <b>ЗАПИСИ НА НЕДЕЛЮ</b>\n"
    text += f"📆 {today.strftime('%d.%m.%Y')} — {(today + timedelta(days=7)).strftime('%d.%m.%Y')}\n"
    text += f"📊 Всего заказов: {len(orders)}\n\n"
    
    for i, order in enumerate(orders[:5]):
        text += format_order(order, show_items=True)
        if i < min(len(orders), 5) - 1:
            text += "\n━━━━━━━━━━━━━━━━\n\n"
    
    if len(orders) > 5:
        text += f"\n<i>... и ещё {len(orders) - 5} заказов</i>\n"
        text += f"<i>Используйте 'Календарь' для полного просмотра</i>"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        text,
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
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
        await callback.answer()
        return
    
    text = f"📊 <b>КАЛЕНДАРЬ НА МЕСЯЦ</b>\n"
    text += f"📆 {today.strftime('%d.%m.%Y')} — {(today + timedelta(days=30)).strftime('%d.%m.%Y')}\n"
    text += f"📋 Всего заказов: {len(orders)}\n\n"
    
    for i, order in enumerate(orders[:5]):
        text += format_order(order, show_items=True)
        if i < min(len(orders), 5) - 1:
            text += "\n━━━━━━━━━━━━━━━━\n\n"
    
    if len(orders) > 5:
        text += f"\n<i>Показано 5 из {len(orders)} заказов</i>\n"
        text += f"<i>Используйте 'Отчёты' для полного списка</i>"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        text,
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()