from datetime import datetime
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import OrderEditStates
from utils import get_main_keyboard, edit_or_send, format_order, parse_date_range

router = Router()

from database import get_database
db = get_database()


@router.callback_query(F.data == "edit_booking_menu")
async def edit_booking_menu(callback: CallbackQuery):
    """Меню редактирования броней"""
    orders = db.get_all_active_orders()
    
    if not orders:
        await edit_or_send(
            callback,
            "✏️ <b>Редактирование броней</b>\n\n"
            "❌ Активных броней не найдено.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await callback.answer()
        return
    
    text = f"✏️ <b>Редактирование броней</b>\n"
    text += f"📊 Активных броней: {len(orders)}\n\n"
    text += "Выберите бронь для редактирования:"
    
    builder = InlineKeyboardBuilder()
    for order in orders[:10]:
        order_id, client_name, _, start_date, end_date = order[:5]
        builder.row(InlineKeyboardButton(
            text=f"#{order_id} | {client_name} | {start_date}",
            callback_data=f"editorder_{order_id}"
        ))
    
    if len(orders) > 10:
        text += f"\n<i>Показаны первые 10 из {len(orders)} броней</i>"
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("editorder_"))
async def choose_field_to_edit(callback: CallbackQuery, state: FSMContext):
    """Выбор поля заказа для редактирования"""
    order_id = int(callback.data.split("_")[1])
    order = db.get_order_details(order_id)
    
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    await state.update_data(edit_order_id=order_id)
    
    text = "✏️ <b>Редактирование заказа</b>\n\n"
    text += format_order(order, show_items=True)
    text += "\n<b>Что хотите изменить?</b>"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Даты", callback_data=f"editorderfield_dates_{order_id}"))
    builder.row(InlineKeyboardButton(text="💰 Стоимость", callback_data=f"editorderfield_cost_{order_id}"))
    builder.row(InlineKeyboardButton(text="💬 Комментарий", callback_data=f"editorderfield_comment_{order_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="edit_booking_menu"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("editorderfield_"))
async def start_edit_order_field(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования поля заказа"""
    parts = callback.data.split("_")
    field = parts[1]
    order_id = int(parts[2])
    
    await state.update_data(edit_order_id=order_id, edit_field=field)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"editorder_{order_id}"))
    
    if field == 'dates':
        prompt = "📅 <b>Введите новые даты:</b>\nФормат: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД"
        next_state = OrderEditStates.entering_new_dates
    elif field == 'cost':
        prompt = "💰 <b>Введите новую стоимость:</b>"
        next_state = OrderEditStates.entering_new_cost
    else:  # comment
        prompt = "💬 <b>Введите новый комментарий:</b>"
        next_state = OrderEditStates.entering_new_comment
    
    await edit_or_send(
        callback,
        f"✏️ <b>Редактирование заказа #{order_id}</b>\n\n{prompt}",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(next_state)
    await callback.answer()


@router.message(OrderEditStates.entering_new_dates)
async def process_new_dates(message: Message, state: FSMContext):
    """Обработка новых дат"""
    dates, error = parse_date_range(message.text)
    
    if error:
        await message.answer(f"{error}\n\nПовторите ввод:")
        return
    
    start_date, end_date = dates
    data = await state.get_data()
    order_id = data['edit_order_id']
    
    # Проверяем доступность всех ресурсов на новые даты
    items = db.get_order_items(order_id)
    unavailable = []
    
    for _, resource_name, quantity, resource_id in items:
        if not db.check_availability(resource_id, start_date, end_date, quantity, order_id):
            available = db.get_available_quantity(resource_id, start_date, end_date, order_id)
            unavailable.append(f"• {resource_name}: нужно {quantity}, доступно {available}")
    
    if unavailable:
        text = "❌ <b>Недостаточно оборудования на новые даты!</b>\n\n"
        text += "\n".join(unavailable)
        text += "\n\nВыберите другие даты или измените количество."
        await message.answer(text, parse_mode='HTML')
        return
    
    # Обновляем даты в базе
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET start_date = ?, end_date = ? WHERE id = ?",
                (start_date, end_date, order_id)
            )
            conn.commit()
        
        await message.answer(
            f"✅ <b>Даты заказа обновлены!</b>\n\n"
            f"Новый период: {start_date} — {end_date}",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    except Exception as e:
        await message.answer(
            "❌ Ошибка при обновлении дат.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()


@router.message(OrderEditStates.entering_new_cost)
async def process_new_cost(message: Message, state: FSMContext):
    """Обработка новой стоимости"""
    data = await state.get_data()
    order_id = data['edit_order_id']
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET cost = ? WHERE id = ?",
                (message.text, order_id)
            )
            conn.commit()
        
        await message.answer(
            f"✅ <b>Стоимость заказа обновлена!</b>\n\n"
            f"Новая стоимость: {message.text}",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    except Exception as e:
        await message.answer(
            "❌ Ошибка при обновлении стоимости.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()


@router.message(OrderEditStates.entering_new_comment)
async def process_new_comment(message: Message, state: FSMContext):
    """Обработка нового комментария"""
    data = await state.get_data()
    order_id = data['edit_order_id']
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET delivery_comment = ? WHERE id = ?",
                (message.text, order_id)
            )
            conn.commit()
        
        await message.answer(
            f"✅ <b>Комментарий заказа обновлён!</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    except Exception as e:
        await message.answer(
            "❌ Ошибка при обновлении комментария.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()