from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import is_admin, logger
from utils import get_main_keyboard, edit_or_send

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    if not is_admin(message.from_user.id):
        logger.warning(f"Неавторизованный доступ от user_id: {message.from_user.id}")
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    
    await state.clear()
    logger.info(f"Администратор {message.from_user.id} запустил бота")
    
    await message.answer(
        "🏢 <b>Система бронирования оборудования</b>\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """Обработка команды /menu"""
    if not is_admin(message.from_user.id):
        return
    
    await state.clear()
    await message.answer(
        "🏢 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await edit_or_send(
        callback,
        "🏢 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await edit_or_send(
        callback,
        "❌ Действие отменено.\n\n"
        "🏢 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    await callback.answer()