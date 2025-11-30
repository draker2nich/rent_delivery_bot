from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from states import BookingStates
from utils import get_main_keyboard, edit_or_send, parse_date_range

router = Router()
db = Database()


@router.callback_query(F.data == "create_booking")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начало процесса создания брони"""
    resources = db.get_resources()
    
    if not resources:
        await edit_or_send(
            callback,
            "❌ Нет доступных ресурсов.\n\n"
            "Сначала добавьте оборудование в разделе 'Управление ресурсами'.",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return
    
    builder = InlineKeyboardBuilder()
    for res_id, name, _, quantity in resources:
        builder.row(InlineKeyboardButton(
            text=f"{name} (всего: {quantity} шт.)",
            callback_data=f"resource_{res_id}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        "📝 <b>Создание брони</b>\n\n"
        "🎯 Выберите оборудование:",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.choosing_resource)
    await callback.answer()


@router.callback_query(BookingStates.choosing_resource, F.data.startswith("resource_"))
async def choose_resource(callback: CallbackQuery, state: FSMContext):
    """Выбор ресурса для бронирования"""
    resource_id = int(callback.data.split("_")[1])
    resource_info = db.get_resource_info(resource_id)
    
    if not resource_info:
        await edit_or_send(callback, "❌ Ресурс не найден.", reply_markup=get_main_keyboard())
        await callback.answer()
        return
    
    _, name, total_quantity = resource_info
    await state.update_data(resource_id=resource_id, resource_name=name, total_quantity=total_quantity)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await edit_or_send(
        callback,
        f"📝 <b>Создание брони</b>\n\n"
        f"🎯 Выбрано: {name}\n"
        f"📦 Доступно всего: {total_quantity} шт.\n\n"
        f"<b>Введите количество:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_quantity)
    await callback.answer()


@router.message(BookingStates.entering_quantity)
async def enter_quantity(message: Message, state: FSMContext):
    """Ввод количества оборудования"""
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше 0!\n\nПовторите ввод:")
            return
        
        data = await state.get_data()
        if quantity > data['total_quantity']:
            await message.answer(
                f"❌ Недостаточно оборудования!\n"
                f"Доступно всего: {data['total_quantity']} шт.\n\n"
                f"Повторите ввод:"
            )
            return
        
        await state.update_data(quantity=quantity)
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
        
        await message.answer(
            f"📝 <b>Создание брони</b>\n\n"
            f"🎯 Оборудование: {data['resource_name']}\n"
            f"📦 Количество: {quantity} шт.\n\n"
            f"<b>Введите даты аренды:</b>\n"
            f"Формат: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД\n\n"
            f"Пример: 2024-12-25 - 2024-12-27",
            reply_markup=builder.as_markup(),
            parse_mode='HTML'
        )
        await state.set_state(BookingStates.entering_dates)
        
    except ValueError:
        await message.answer("❌ Введите корректное число!")


@router.message(BookingStates.entering_dates)
async def enter_dates(message: Message, state: FSMContext):
    """Ввод дат бронирования"""
    dates, error = parse_date_range(message.text)
    
    if error:
        await message.answer(f"{error}\n\nПовторите ввод:")
        return
    
    start_date, end_date = dates
    data = await state.get_data()
    
    available = db.get_available_quantity(data['resource_id'], start_date, end_date)
    
    if available < data['quantity']:
        await message.answer(
            f"❌ Недостаточно оборудования на указанные даты!\n\n"
            f"Запрошено: {data['quantity']} шт.\n"
            f"Доступно: {available} шт.\n\n"
            f"Попробуйте выбрать другие даты или уменьшите количество."
        )
        return
    
    await state.update_data(start_date=start_date, end_date=end_date)
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end_dt - start_dt).days + 1
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Верно", callback_data="confirm_yes"),
        InlineKeyboardButton(text="❌ Изменить", callback_data="confirm_no")
    )
    
    await message.answer(
        f"📝 <b>Проверьте данные:</b>\n\n"
        f"🎯 Оборудование: {data['resource_name']}\n"
        f"📦 Количество: {data['quantity']} шт.\n"
        f"📅 Начало: {start_date}\n"
        f"📅 Конец: {end_date}\n"
        f"⏱ Срок: {days} {'день' if days == 1 else 'дня' if days < 5 else 'дней'}\n"
        f"✅ Доступно: {available} шт.\n\n"
        f"<b>Всё верно?</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.confirming_dates)


@router.callback_query(BookingStates.confirming_dates, F.data == "confirm_yes")
async def confirm_dates_yes(callback: CallbackQuery, state: FSMContext):
    """Подтверждение дат"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await edit_or_send(
        callback,
        "📝 <b>Создание брони</b>\n\n"
        "<b>Введите ФИО клиента:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_client_name)
    await callback.answer()


@router.callback_query(BookingStates.confirming_dates, F.data == "confirm_no")
async def confirm_dates_no(callback: CallbackQuery, state: FSMContext):
    """Отмена подтверждения дат"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await edit_or_send(
        callback,
        "📝 <b>Создание брони</b>\n\n"
        "<b>Введите даты заново:</b>\n"
        "Формат: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_dates)
    await callback.answer()


@router.message(BookingStates.entering_client_name)
async def enter_client_name(message: Message, state: FSMContext):
    """Ввод имени клиента"""
    await state.update_data(client_name=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await message.answer(
        "📝 <b>Создание брони</b>\n\n"
        "<b>Введите номер телефона клиента:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_client_phone)


@router.message(BookingStates.entering_client_phone)
async def enter_client_phone(message: Message, state: FSMContext):
    """Ввод телефона клиента"""
    await state.update_data(client_phone=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏃 Самовывоз", callback_data="delivery_pickup"))
    builder.row(InlineKeyboardButton(text="🚗 Доставка", callback_data="delivery_delivery"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await message.answer(
        "📝 <b>Создание брони</b>\n\n"
        "🚚 <b>Выберите тип получения:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.choosing_delivery_type)


@router.callback_query(BookingStates.choosing_delivery_type, F.data.startswith("delivery_"))
async def choose_delivery_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа доставки"""
    delivery_type = callback.data.split("_")[1]
    await state.update_data(delivery_type=delivery_type)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    if delivery_type == 'pickup':
        prompt = "💬 <b>Введите комментарий:</b>\n(время самовывоза, примечания)"
    else:
        prompt = "💬 <b>Введите адрес доставки и время:</b>"
    
    await edit_or_send(
        callback,
        f"📝 <b>Создание брони</b>\n\n{prompt}",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_delivery_comment)
    await callback.answer()


@router.message(BookingStates.entering_delivery_comment)
async def enter_delivery_comment(message: Message, state: FSMContext):
    """Ввод комментария к доставке"""
    await state.update_data(delivery_comment=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await message.answer(
        "📝 <b>Создание брони</b>\n\n"
        "💰 <b>Введите стоимость аренды:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_cost)


@router.message(BookingStates.entering_cost)
async def enter_cost(message: Message, state: FSMContext):
    """Ввод стоимости и создание брони"""
    data = await state.get_data()
    
    booking_id = db.create_booking(
        resource_id=data['resource_id'],
        client_name=data['client_name'],
        client_phone=data['client_phone'],
        start_date=data['start_date'],
        end_date=data['end_date'],
        quantity=data['quantity'],
        delivery_type=data['delivery_type'],
        delivery_comment=data['delivery_comment'],
        cost=message.text,
        created_by=message.from_user.id
    )
    
    if booking_id:
        delivery_emoji = "🚗" if data['delivery_type'] == 'delivery' else "🏃"
        delivery_text = "Доставка" if data['delivery_type'] == 'delivery' else "Самовывоз"
        
        await message.answer(
            f"✅ <b>Бронь #{booking_id} успешно создана!</b>\n\n"
            f"🎯 Оборудование: {data['resource_name']}\n"
            f"📦 Количество: {data['quantity']} шт.\n"
            f"📅 Период: {data['start_date']} — {data['end_date']}\n"
            f"👤 Клиент: {data['client_name']}\n"
            f"📞 Телефон: {data['client_phone']}\n"
            f"{delivery_emoji} Тип: {delivery_text}\n"
            f"💬 Комментарий: {data['delivery_comment']}\n"
            f"💰 Стоимость: {message.text}",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await message.answer(
            "❌ Ошибка создания брони.\n"
            "Возможно, оборудование уже занято на эти даты.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()