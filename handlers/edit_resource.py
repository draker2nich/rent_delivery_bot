from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from states import ResourceStates
from utils import get_main_keyboard, edit_or_send

router = Router()
db = Database()


@router.callback_query(F.data == "edit_resource_menu")
async def edit_resource_menu(callback: CallbackQuery):
    """Меню редактирования ресурсов"""
    resources = db.get_resources()
    
    if not resources:
        await edit_or_send(
            callback,
            "✏️ <b>Редактирование ресурсов</b>\n\n"
            "❌ Ресурсы не найдены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await callback.answer()
        return
    
    text = "✏️ <b>Редактирование ресурсов</b>\n\n"
    text += "Выберите ресурс для редактирования:"
    
    builder = InlineKeyboardBuilder()
    for res_id, name, desc, quantity in resources:
        builder.row(InlineKeyboardButton(
            text=f"✏️ {name} ({quantity} шт.)",
            callback_data=f"editres_{res_id}"
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="manage_resources"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("editres_"))
async def choose_edit_field(callback: CallbackQuery, state: FSMContext):
    """Выбор поля для редактирования"""
    resource_id = int(callback.data.split("_")[1])
    resource = db.get_resource_info(resource_id)
    
    if not resource:
        await callback.answer("❌ Ресурс не найден", show_alert=True)
        return
    
    res_id, name, quantity = resource
    
    # Получаем полную информацию
    resources = db.get_resources()
    description = ""
    for r in resources:
        if r[0] == res_id:
            description = r[2] or "Не указано"
            break
    
    await state.update_data(edit_resource_id=resource_id)
    
    text = f"✏️ <b>Редактирование ресурса</b>\n\n"
    text += f"🎯 <b>{name}</b>\n"
    text += f"📝 Описание: {description}\n"
    text += f"📦 Количество: {quantity} шт.\n\n"
    text += "Что хотите изменить?"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Название", callback_data=f"editfield_name_{resource_id}"))
    builder.row(InlineKeyboardButton(text="📄 Описание", callback_data=f"editfield_description_{resource_id}"))
    builder.row(InlineKeyboardButton(text="📦 Количество", callback_data=f"editfield_quantity_{resource_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="edit_resource_menu"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("editfield_"))
async def start_edit_field(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования поля"""
    parts = callback.data.split("_")
    field = parts[1]
    resource_id = int(parts[2])
    
    await state.update_data(edit_resource_id=resource_id, edit_field=field)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"editres_{resource_id}"))
    
    prompts = {
        'name': "📝 Введите новое название:",
        'description': "📄 Введите новое описание:\n(или '-' для очистки)",
        'quantity': "📦 Введите новое количество:"
    }
    
    await edit_or_send(
        callback,
        f"✏️ <b>Редактирование ресурса</b>\n\n{prompts[field]}",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(ResourceStates.entering_new_value)
    await callback.answer()


@router.message(ResourceStates.entering_new_value)
async def process_edit_value(message: Message, state: FSMContext):
    """Обработка нового значения"""
    data = await state.get_data()
    resource_id = data['edit_resource_id']
    field = data['edit_field']
    
    success = False
    
    if field == 'name':
        success = db.update_resource(resource_id, name=message.text)
    elif field == 'description':
        desc = message.text if message.text != '-' else ''
        success = db.update_resource(resource_id, description=desc)
    elif field == 'quantity':
        try:
            quantity = int(message.text)
            if quantity <= 0:
                await message.answer("❌ Количество должно быть больше 0!")
                return
            success = db.update_resource(resource_id, total_quantity=quantity)
        except ValueError:
            await message.answer("❌ Введите корректное число!")
            return
    
    if success:
        await message.answer(
            "✅ <b>Ресурс успешно обновлён!</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await message.answer(
            "❌ Ошибка при обновлении ресурса.",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()