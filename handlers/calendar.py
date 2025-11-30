from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import get_main_keyboard, edit_or_send

router = Router()
from database import get_database
db = get_database()


@router.callback_query(F.data == "calendar_availability")
async def calendar_availability(callback: CallbackQuery):
    """Календарь загруженности ресурсов"""
    resources = db.get_resources()
    
    if not resources:
        await edit_or_send(
            callback,
            "📊 <b>Календарь загруженности</b>\n\n"
            "❌ Нет доступных ресурсов.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await callback.answer()
        return
    
    text = "📊 <b>КАЛЕНДАРЬ ЗАГРУЖЕННОСТИ</b>\n\n"
    text += "Выберите ресурс для просмотра:"
    
    builder = InlineKeyboardBuilder()
    for res_id, name, _, quantity in resources:
        builder.row(InlineKeyboardButton(
            text=f"📦 {name} ({quantity} шт.)",
            callback_data=f"calres_{res_id}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("calres_"))
async def show_resource_calendar(callback: CallbackQuery):
    """Показать календарь для конкретного ресурса"""
    resource_id = int(callback.data.split("_")[1])
    resource_info = db.get_resource_info(resource_id)
    
    if not resource_info:
        await callback.answer("❌ Ресурс не найден", show_alert=True)
        return
    
    _, name, total_quantity = resource_info
    
    # Генерируем календарь на 14 дней вперед
    today = datetime.now().date()
    
    text = f"📊 <b>КАЛЕНДАРЬ ЗАГРУЖЕННОСТИ</b>\n\n"
    text += f"🎯 Ресурс: {name}\n"
    text += f"📦 Всего: {total_quantity} шт.\n\n"
    text += "📅 <b>Загруженность на 14 дней:</b>\n\n"
    
    for i in range(14):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime('%Y-%m-%d')
        
        available = db.get_available_quantity(resource_id, date_str, date_str)
        booked = total_quantity - available
        
        # Определяем статус
        if available == total_quantity:
            status = "🟢 Свободно"
            status_icon = "🟢"
        elif available > 0:
            status = f"🟡 Частично ({booked}/{total_quantity})"
            status_icon = "🟡"
        else:
            status = "🔴 Занято"
            status_icon = "🔴"
        
        # Форматируем дату
        date_display = check_date.strftime('%d.%m')
        weekday = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][check_date.weekday()]
        
        if i == 0:
            text += f"{status_icon} <b>Сегодня</b> ({date_display}, {weekday})\n"
        elif i == 1:
            text += f"{status_icon} <b>Завтра</b> ({date_display}, {weekday})\n"
        else:
            text += f"{status_icon} {date_display} ({weekday})\n"
        
        text += f"   Доступно: {available} шт.\n"
        if booked > 0:
            text += f"   Забронировано: {booked} шт.\n"
        text += "\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ К списку ресурсов", callback_data="calendar_availability"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()