from datetime import datetime
from aiogram import F, Router
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
    """Начало процесса создания брони - выбор клиента"""
    clients = db.get_all_clients()
    
    builder = InlineKeyboardBuilder()
    
    # Показываем последних 10 клиентов
    for client_id, name, phone, order_count, _ in clients[:10]:
        builder.row(InlineKeyboardButton(
            text=f"👤 {name} ({phone})",
            callback_data=f"selectclient_{client_id}"
        ))
    
    builder.row(InlineKeyboardButton(text="➕ Новый клиент", callback_data="new_client"))
    
    if len(clients) > 10:
        builder.row(InlineKeyboardButton(text="📋 Все клиенты", callback_data="all_clients"))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        "📝 <b>Создание брони</b>\n\n"
        "👥 <b>Выберите клиента или создайте нового:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.choosing_client)
    await callback.answer()


@router.callback_query(F.data == "all_clients")
async def show_all_clients(callback: CallbackQuery, state: FSMContext):
    """Показать всех клиентов"""
    clients = db.get_all_clients()
    
    if not clients:
        await callback.answer("❌ Клиенты не найдены", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    
    for client_id, name, phone, order_count, _ in clients:
        builder.row(InlineKeyboardButton(
            text=f"👤 {name} ({phone}) - {order_count} заказ.",
            callback_data=f"selectclient_{client_id}"
        ))
    
    builder.row(InlineKeyboardButton(text="➕ Новый клиент", callback_data="new_client"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="create_booking"))
    
    await edit_or_send(
        callback,
        f"📝 <b>Создание брони</b>\n\n"
        f"👥 <b>Все клиенты ({len(clients)}):</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_client, F.data.startswith("selectclient_"))
async def select_existing_client(callback: CallbackQuery, state: FSMContext):
    """Выбор существующего клиента"""
    client_id = int(callback.data.split("_")[1])
    client = db.get_client_by_id(client_id)
    
    if not client:
        await callback.answer("❌ Клиент не найден", show_alert=True)
        return
    
    _, name, phone = client
    await state.update_data(client_id=client_id, client_name=name, client_phone=phone)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await edit_or_send(
        callback,
        f"📝 <b>Создание брони</b>\n\n"
        f"👤 Клиент: {name}\n"
        f"📞 Телефон: {phone}\n\n"
        f"<b>Введите даты аренды:</b>\n"
        f"Формат: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД\n\n"
        f"Пример: 2024-12-25 - 2024-12-27",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_dates)
    await callback.answer()


@router.callback_query(BookingStates.choosing_client, F.data == "new_client")
async def create_new_client(callback: CallbackQuery, state: FSMContext):
    """Создание нового клиента"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await edit_or_send(
        callback,
        "📝 <b>Создание брони</b>\n\n"
        "👤 <b>Новый клиент</b>\n\n"
        "<b>Введите ФИО клиента:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_client_name)
    await callback.answer()


@router.message(BookingStates.entering_client_name)
async def enter_client_name(message: Message, state: FSMContext):
    """Ввод имени нового клиента"""
    await state.update_data(client_name=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await message.answer(
        "📝 <b>Создание брони</b>\n\n"
        "📞 <b>Введите номер телефона:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_client_phone)


@router.message(BookingStates.entering_client_phone)
async def enter_client_phone(message: Message, state: FSMContext):
    """Ввод телефона нового клиента"""
    data = await state.get_data()
    client_id = db.add_client(data['client_name'], message.text)
    
    await state.update_data(client_id=client_id, client_phone=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await message.answer(
        f"📝 <b>Создание брони</b>\n\n"
        f"✅ Клиент сохранён\n"
        f"👤 {data['client_name']}\n"
        f"📞 {message.text}\n\n"
        f"<b>Введите даты аренды:</b>\n"
        f"Формат: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД\n\n"
        f"Пример: 2024-12-25 - 2024-12-27",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_dates)


@router.message(BookingStates.entering_dates)
async def enter_dates(message: Message, state: FSMContext):
    """Ввод дат бронирования"""
    dates, error = parse_date_range(message.text)
    
    if error:
        await message.answer(f"{error}\n\nПовторите ввод:")
        return
    
    start_date, end_date = dates
    await state.update_data(start_date=start_date, end_date=end_date, order_items=[])
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end_dt - start_dt).days + 1
    
    data = await state.get_data()
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Верно", callback_data="confirm_dates_yes"),
        InlineKeyboardButton(text="❌ Изменить", callback_data="confirm_dates_no")
    )
    
    await message.answer(
        f"📝 <b>Проверьте данные:</b>\n\n"
        f"👤 Клиент: {data['client_name']}\n"
        f"📞 Телефон: {data['client_phone']}\n"
        f"📅 Начало: {start_date}\n"
        f"📅 Конец: {end_date}\n"
        f"⏱ Срок: {days} {'день' if days == 1 else 'дня' if days < 5 else 'дней'}\n\n"
        f"<b>Всё верно?</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.confirming_dates)


@router.callback_query(BookingStates.confirming_dates, F.data == "confirm_dates_yes")
async def confirm_dates_yes(callback: CallbackQuery, state: FSMContext):
    """Подтверждение дат - переход к выбору ресурсов"""
    await show_resources_menu(callback, state)


@router.callback_query(BookingStates.confirming_dates, F.data == "confirm_dates_no")
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


async def show_resources_menu(callback: CallbackQuery, state: FSMContext):
    """Показать меню выбора ресурсов"""
    resources = db.get_resources()
    data = await state.get_data()
    
    if not resources:
        await edit_or_send(
            callback,
            "❌ Нет доступных ресурсов.\n\n"
            "Сначала добавьте оборудование в разделе 'Управление ресурсами'.",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return
    
    order_items = data.get('order_items', [])
    
    text = "📝 <b>Добавление оборудования</b>\n\n"
    
    if order_items:
        text += "✅ <b>Уже добавлено:</b>\n"
        for item in order_items:
            text += f"   • {item['name']}: {item['quantity']} шт.\n"
        text += "\n"
    
    text += "🎯 <b>Выберите оборудование для добавления:</b>"
    
    builder = InlineKeyboardBuilder()
    
    for res_id, name, _, total_quantity in resources:
        available = db.get_available_quantity(
            res_id,
            data['start_date'],
            data['end_date']
        )
        
        # Учитываем уже добавленные позиции
        for item in order_items:
            if item['resource_id'] == res_id:
                available -= item['quantity']
        
        if available > 0:
            builder.row(InlineKeyboardButton(
                text=f"{name} (доступно: {available} шт.)",
                callback_data=f"addres_{res_id}"
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"❌ {name} (нет в наличии)",
                callback_data="unavailable"
            ))
    
    if order_items:
        builder.row(InlineKeyboardButton(
            text="✅ Завершить и перейти к доставке",
            callback_data="finish_adding_resources"
        ))
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await state.set_state(BookingStates.choosing_resource)
    await callback.answer()


@router.callback_query(F.data == "unavailable")
async def resource_unavailable(callback: CallbackQuery):
    """Уведомление о недоступности ресурса"""
    await callback.answer("❌ Это оборудование недоступно на выбранные даты", show_alert=True)


@router.callback_query(BookingStates.choosing_resource, F.data.startswith("addres_"))
async def add_resource_to_order(callback: CallbackQuery, state: FSMContext):
    """Добавление ресурса в заказ"""
    resource_id = int(callback.data.split("_")[1])
    resource_info = db.get_resource_info(resource_id)
    
    if not resource_info:
        await callback.answer("❌ Ресурс не найден", show_alert=True)
        return
    
    _, name, total_quantity = resource_info
    data = await state.get_data()
    
    # Проверяем доступность
    available = db.get_available_quantity(
        resource_id,
        data['start_date'],
        data['end_date']
    )
    
    # Учитываем уже добавленные позиции
    order_items = data.get('order_items', [])
    for item in order_items:
        if item['resource_id'] == resource_id:
            available -= item['quantity']
    
    if available <= 0:
        await callback.answer("❌ Это оборудование уже недоступно", show_alert=True)
        return
    
    await state.update_data(
        current_resource_id=resource_id,
        current_resource_name=name,
        available_quantity=available
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_resources"))
    
    await edit_or_send(
        callback,
        f"📝 <b>Добавление оборудования</b>\n\n"
        f"🎯 Выбрано: {name}\n"
        f"📦 Доступно: {available} шт.\n\n"
        f"<b>Введите количество:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(BookingStates.entering_quantity)
    await callback.answer()


@router.callback_query(F.data == "back_to_resources")
async def back_to_resources(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору ресурсов"""
    await show_resources_menu(callback, state)


@router.message(BookingStates.entering_quantity)
async def enter_quantity(message: Message, state: FSMContext):
    """Ввод количества оборудования"""
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше 0!\n\nПовторите ввод:")
            return
        
        data = await state.get_data()
        
        if quantity > data['available_quantity']:
            await message.answer(
                f"❌ Недостаточно оборудования!\n"
                f"Доступно: {data['available_quantity']} шт.\n\n"
                f"Повторите ввод:"
            )
            return
        
        # Добавляем позицию в список
        order_items = data.get('order_items', [])
        order_items.append({
            'resource_id': data['current_resource_id'],
            'name': data['current_resource_name'],
            'quantity': quantity
        })
        
        await state.update_data(order_items=order_items)
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="➕ Добавить ещё оборудование",
            callback_data="add_more_resources"
        ))
        builder.row(InlineKeyboardButton(
            text="✅ Завершить и перейти к доставке",
            callback_data="finish_adding_resources"
        ))
        
        text = f"✅ <b>Оборудование добавлено!</b>\n\n"
        text += f"📦 {data['current_resource_name']}: {quantity} шт.\n\n"
        text += "<b>Список оборудования в заказе:</b>\n"
        for item in order_items:
            text += f"   • {item['name']}: {item['quantity']} шт.\n"
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode='HTML')
        await state.set_state(BookingStates.adding_resources)
        
    except ValueError:
        await message.answer("❌ Введите корректное число!")


@router.callback_query(BookingStates.adding_resources, F.data == "add_more_resources")
async def add_more_resources(callback: CallbackQuery, state: FSMContext):
    """Добавить ещё ресурсы"""
    await show_resources_menu(callback, state)


@router.callback_query(F.data == "finish_adding_resources")
async def finish_adding_resources(callback: CallbackQuery, state: FSMContext):
    """Завершение добавления ресурсов - переход к доставке"""
    data = await state.get_data()
    order_items = data.get('order_items', [])
    
    if not order_items:
        await callback.answer("❌ Добавьте хотя бы одну позицию!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏃 Самовывоз", callback_data="delivery_pickup"))
    builder.row(InlineKeyboardButton(text="🚗 Доставка", callback_data="delivery_delivery"))
    builder.row(InlineKeyboardButton(text="◀️ Назад к выбору", callback_data="add_more_resources"))
    
    text = "📝 <b>Создание брони</b>\n\n"
    text += "<b>Оборудование в заказе:</b>\n"
    for item in order_items:
        text += f"   • {item['name']}: {item['quantity']} шт.\n"
    text += "\n🚚 <b>Выберите тип получения:</b>"
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await state.set_state(BookingStates.choosing_delivery_type)
    await callback.answer()


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
    
    # Создаем заказ
    order_id = db.create_order(
        client_id=data['client_id'],
        start_date=data['start_date'],
        end_date=data['end_date'],
        delivery_type=data['delivery_type'],
        delivery_comment=data['delivery_comment'],
        cost=message.text,
        created_by=message.from_user.id
    )
    
    if not order_id:
        await message.answer(
            "❌ Ошибка создания заказа.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return
    
    # Добавляем все позиции
    success = True
    for item in data['order_items']:
        if not db.add_order_item(order_id, item['resource_id'], item['quantity']):
            success = False
            break
    
    if success:
        delivery_emoji = "🚗" if data['delivery_type'] == 'delivery' else "🏃"
        delivery_text = "Доставка" if data['delivery_type'] == 'delivery' else "Самовывоз"
        
        text = f"✅ <b>Заказ #{order_id} успешно создан!</b>\n\n"
        text += f"👤 Клиент: {data['client_name']}\n"
        text += f"📞 Телефон: {data['client_phone']}\n"
        text += f"📅 Период: {data['start_date']} — {data['end_date']}\n\n"
        text += "<b>Оборудование:</b>\n"
        for item in data['order_items']:
            text += f"   • {item['name']}: {item['quantity']} шт.\n"
        text += f"\n{delivery_emoji} Тип: {delivery_text}\n"
        text += f"💬 Комментарий: {data['delivery_comment']}\n"
        text += f"💰 Стоимость: {message.text}"
        
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode='HTML')
    else:
        db.delete_order(order_id)
        await message.answer(
            "❌ Ошибка добавления позиций в заказ.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()