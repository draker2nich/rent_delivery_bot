from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from states import ResourceStates
from utils import get_main_keyboard, edit_or_send

router = Router()
db = Database()


@router.callback_query(F.data == "manage_resources")
async def manage_resources_menu(callback: CallbackQuery):
    """Меню управления ресурсами"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить ресурс", callback_data="add_resource"))
    builder.row(InlineKeyboardButton(text="📋 Список ресурсов", callback_data="list_resources"))
    builder.row(InlineKeyboardButton(text="🗑️ Удалить ресурс", callback_data="delete_resource_menu"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        "⚙️ <b>Управление ресурсами</b>\n\n"
        "Выберите действие:",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "add_resource")
async def add_resource_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления ресурса"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="manage_resources"))
    
    await edit_or_send(
        callback,
        "➕ <b>Добавление оборудования</b>\n\n"
        "<b>Введите название:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(ResourceStates.entering_name)
    await callback.answer()


@router.message(ResourceStates.entering_name)
async def add_resource_name(message: Message, state: FSMContext):
    """Ввод названия ресурса"""
    await state.update_data(name=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="manage_resources"))
    
    await message.answer(
        "➕ <b>Добавление оборудования</b>\n\n"
        "<b>Введите описание:</b>\n"
        "(или '-' для пропуска)",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(ResourceStates.entering_description)


@router.message(ResourceStates.entering_description)
async def add_resource_description(message: Message, state: FSMContext):
    """Ввод описания ресурса"""
    description = message.text if message.text != '-' else ''
    await state.update_data(description=description)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="manage_resources"))
    
    await message.answer(
        "➕ <b>Добавление оборудования</b>\n\n"
        "📦 <b>Введите общее количество:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(ResourceStates.entering_quantity)


@router.message(ResourceStates.entering_quantity)
async def add_resource_quantity(message: Message, state: FSMContext):
    """Ввод количества и создание ресурса"""
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("❌ Количество должно быть больше 0!\n\nПовторите ввод:")
            return
        
        data = await state.get_data()
        
        if db.add_resource(data['name'], data['description'], quantity):
            await message.answer(
                f"✅ <b>Оборудование добавлено!</b>\n\n"
                f"🎯 Название: {data['name']}\n"
                f"📦 Количество: {quantity} шт.",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
        else:
            await message.answer(
                f"❌ Оборудование '{data['name']}' уже существует.",
                reply_markup=get_main_keyboard()
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное число!")


@router.callback_query(F.data == "list_resources")
async def list_resources(callback: CallbackQuery):
    """Список всех ресурсов"""
    resources = db.get_resources()
    
    if not resources:
        await edit_or_send(
            callback,
            "📋 <b>Список оборудования</b>\n\n"
            "❌ Оборудование не найдено.\n\n"
            "Добавьте новое оборудование через меню.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        text = f"📋 <b>СПИСОК ОБОРУДОВАНИЯ</b>\n"
        text += f"📊 Всего позиций: {len(resources)}\n\n"
        
        for res_id, name, desc, quantity in resources:
            text += f"🎯 <b>{name}</b>\n"
            text += f"   📦 Количество: {quantity} шт.\n"
            if desc:
                text += f"   📝 {desc}\n"
            text += f"   🔑 ID: {res_id}\n\n"
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="manage_resources"))
        
        await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    
    await callback.answer()


@router.callback_query(F.data == "delete_resource_menu")
async def delete_resource_menu(callback: CallbackQuery):
    """Меню удаления ресурса"""
    resources = db.get_resources()
    
    if not resources:
        await edit_or_send(
            callback,
            "🗑️ <b>Удаление оборудования</b>\n\n"
            "❌ Оборудование не найдено.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await callback.answer()
        return
    
    text = "🗑️ <b>Удаление оборудования</b>\n\n"
    text += "Выберите оборудование для удаления:"
    
    builder = InlineKeyboardBuilder()
    for res_id, name, _, quantity in resources:
        builder.row(InlineKeyboardButton(
            text=f"🗑️ {name} ({quantity} шт.)",
            callback_data=f"delres_{res_id}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="manage_resources"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("delres_"))
async def delete_resource_confirm(callback: CallbackQuery):
    """Удаление ресурса"""
    resource_id = int(callback.data.split("_")[1])
    
    if db.delete_resource(resource_id):
        await callback.answer("✅ Оборудование удалено!", show_alert=True)
        await manage_resources_menu(callback)
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)