from datetime import datetime, timedelta
from typing import Optional, Tuple
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import logger


def parse_date_range(text: str) -> Tuple[Optional[Tuple[str, str]], Optional[str]]:
    """Парсинг диапазона дат из текста"""
    try:
        if '-' not in text or len(text.split('-')) < 3:
            return None, "❌ Неверный формат. Используйте: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД"
        
        parts = text.split()
        if len(parts) != 3:
            return None, "❌ Неверный формат. Используйте: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД"
        
        start_str = parts[0].strip()
        end_str = parts[2].strip()
        
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
        except ValueError:
            return None, "❌ Неверный формат даты. Проверьте правильность ввода."
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date.date() < today.date():
            return None, "❌ Дата начала не может быть в прошлом!"
        
        if end_date < start_date:
            return None, (
                "❌ Дата окончания не может быть раньше даты начала!\n\n"
                f"Вы указали:\n"
                f"Начало: {start_str}\n"
                f"Конец: {end_str}\n\n"
                f"Проверьте правильность дат."
            )
        
        return (start_str, end_str), None
        
    except Exception as e:
        logger.error(f"Ошибка парсинга дат: {e}")
        return None, "❌ Произошла ошибка при обработке дат. Попробуйте снова."


def format_booking(booking: Tuple, show_actions: bool = False) -> str:
    """Форматирование информации о бронировании"""
    booking_id, resource, client, phone, start, end = booking[:6]
    quantity = booking[6] if len(booking) > 6 else 1
    delivery_type = booking[7] if len(booking) > 7 else 'pickup'
    delivery_comment = booking[8] if len(booking) > 8 else ''
    cost = booking[9] if len(booking) > 9 else ''
    
    delivery_emoji = "🚗" if delivery_type == 'delivery' else "🏃"
    delivery_text = "Доставка" if delivery_type == 'delivery' else "Самовывоз"
    
    today = datetime.now().date()
    start_dt = datetime.strptime(start, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end, '%Y-%m-%d').date()
    
    highlight = ""
    if end_dt == today:
        highlight = "🔴 ЗАБРАТЬ СЕГОДНЯ!\n"
    elif end_dt == today + timedelta(days=1):
        highlight = "🟡 Забрать завтра\n"
    elif start_dt == today:
        highlight = "🟢 Выдать сегодня\n"
    elif start_dt == today + timedelta(days=1):
        highlight = "🟢 Выдать завтра\n"
    
    text = f"{highlight}📋 Бронь #{booking_id}\n"
    text += f"🎯 Оборудование: {resource}\n"
    text += f"📦 Количество: {quantity} шт.\n"
    text += f"👤 Клиент: {client}\n"
    text += f"📞 Телефон: {phone}\n"
    text += f"📅 Период: {start} — {end}\n"
    text += f"{delivery_emoji} Тип: {delivery_text}\n"
    
    if delivery_comment:
        text += f"💬 Комментарий: {delivery_comment}\n"
    
    if cost:
        text += f"💰 Стоимость: {cost}\n"
    
    return text


def get_main_keyboard():
    """Главная клавиатура меню"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Создать бронь", callback_data="create_booking"))
    builder.row(
        InlineKeyboardButton(text="📅 Сегодня", callback_data="tasks_today"),
        InlineKeyboardButton(text="📅 Завтра", callback_data="tasks_tomorrow")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Неделя", callback_data="check_week"),
        InlineKeyboardButton(text="📊 Месяц", callback_data="view_calendar")
    )
    builder.row(InlineKeyboardButton(text="⚙️ Управление ресурсами", callback_data="manage_resources"))
    builder.row(InlineKeyboardButton(text="🗑️ Удалить бронь", callback_data="delete_booking_menu"))
    builder.row(InlineKeyboardButton(text="📈 Отчёты", callback_data="reports_menu"))
    builder.row(InlineKeyboardButton(text="✉️ Отправить сообщение", callback_data="send_message"))
    return builder.as_markup()


async def edit_or_send(callback: CallbackQuery, text: str, reply_markup=None, parse_mode=None):
    """Редактирование существующего сообщения или отправка нового"""
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except:
        await callback.message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )