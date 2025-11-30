from datetime import datetime, timedelta
from typing import Optional, Tuple
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import logger
from database import Database

db = Database()


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


def format_order(order: Tuple, show_items: bool = True) -> str:
    """Форматирование информации о заказе"""
    if not order or len(order) < 5:
        return "❌ Ошибка: неверный формат заказа"
    
    order_id, client_name, client_phone, start, end = order[:5]
    delivery_type = order[5] if len(order) > 5 else 'pickup'
    delivery_comment = order[6] if len(order) > 6 else ''
    cost = order[7] if len(order) > 7 else ''
    status = order[8] if len(order) > 8 else 'active'
    
    delivery_emoji = "🚗" if delivery_type == 'delivery' else "🏃"
    delivery_text = "Доставка" if delivery_type == 'delivery' else "Самовывоз"
    
    try:
        today = datetime.now().date()
        start_dt = datetime.strptime(start, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end, '%Y-%m-%d').date()
        
        highlight = ""
        if end_dt == today:
            highlight = "🔴 "
        elif end_dt == today + timedelta(days=1):
            highlight = "🟡 "
        elif start_dt == today:
            highlight = "🟢 "
        elif start_dt == today + timedelta(days=1):
            highlight = "🟢 "
        
        text = f"{highlight}<b>#{order_id}</b> | {client_name}\n"
        text += f"📞 {client_phone}\n"
        text += f"📅 {start} — {end}\n"
        
        # Получаем позиции заказа
        if show_items:
            try:
                items = db.get_order_items(order_id)
                if items:
                    text += "📦 "
                    items_text = ", ".join([f"{item_name}×{quantity}" for _, item_name, quantity, _ in items])
                    text += f"{items_text}\n"
            except Exception as e:
                logger.error(f"Ошибка получения позиций для заказа {order_id}: {e}")
        
        text += f"{delivery_emoji} {delivery_text}"
        
        if delivery_comment and len(delivery_comment) < 50:
            text += f" ({delivery_comment[:47]}...)" if len(delivery_comment) > 47 else f" ({delivery_comment})"
        
        if cost:
            text += f" | 💰 {cost}"
        
        return text
    except Exception as e:
        logger.error(f"Ошибка форматирования заказа {order_id}: {e}")
        return f"❌ Ошибка форматирования заказа #{order_id}"
    
def format_booking(booking: Tuple, show_actions: bool = False) -> str:
    """Legacy функция для обратной совместимости"""
    # Старый формат: (id, resource_name, client_name, phone, start, end, quantity, ...)
    if len(booking) >= 7:
        booking_id, resource, client, phone, start, end, quantity = booking[:7]
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
    
    # Новый формат заказа
    return format_order(booking, show_items=True)


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
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать бронь", callback_data="edit_booking_menu"),
        InlineKeyboardButton(text="🗑️ Удалить бронь", callback_data="delete_booking_menu")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Отчёты", callback_data="reports_menu"),
        InlineKeyboardButton(text="📊 Загруженность", callback_data="calendar_availability")
    )
    builder.row(
        InlineKeyboardButton(text="✉️ Сообщение", callback_data="send_message"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast_message")
    )
    return builder.as_markup()


async def edit_or_send(callback: CallbackQuery, text: str, reply_markup=None, parse_mode=None):
    """Редактирование существующего сообщения или отправка нового"""
    # Telegram ограничивает сообщения до 4096 символов
    MAX_MESSAGE_LENGTH = 4096
    
    if len(text) > MAX_MESSAGE_LENGTH:
        # Обрезаем текст и добавляем уведомление
        text = text[:MAX_MESSAGE_LENGTH - 100] + "\n\n<i>... сообщение обрезано (слишком длинное)</i>"
    
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