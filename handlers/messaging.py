from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import MessageStates
from utils import get_main_keyboard, edit_or_send
from config import logger

router = Router()


@router.callback_query(F.data == "send_message")
async def send_message_start(callback: CallbackQuery, state: FSMContext):
    """Начало отправки сообщения"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        "✉️ <b>Отправка сообщения</b>\n\n"
        "<b>Введите Telegram ID пользователя:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(MessageStates.entering_user_id)
    await callback.answer()


@router.message(MessageStates.entering_user_id)
async def send_message_get_id(message: Message, state: FSMContext):
    """Ввод ID пользователя"""
    try:
        user_id = int(message.text)
        await state.update_data(target_user_id=user_id)
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main"))
        
        await message.answer(
            "✉️ <b>Отправка сообщения</b>\n\n"
            "<b>Введите текст сообщения:</b>",
            reply_markup=builder.as_markup(),
            parse_mode='HTML'
        )
        await state.set_state(MessageStates.entering_message)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число.")


@router.message(MessageStates.entering_message)
async def send_message_execute(message: Message, state: FSMContext, bot: Bot):
    """Отправка сообщения пользователю"""
    data = await state.get_data()
    target_user_id = data['target_user_id']
    
    try:
        await bot.send_message(target_user_id, message.text)
        await message.answer(
            f"✅ <b>Сообщение отправлено!</b>\n\n"
            f"👤 Получатель: {target_user_id}",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        logger.info(f"Сообщение от {message.from_user.id} к {target_user_id}")
    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка отправки</b>\n\n"
            f"Детали: {str(e)}",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        logger.error(f"Ошибка отправки сообщения: {e}")
    
    await state.clear()