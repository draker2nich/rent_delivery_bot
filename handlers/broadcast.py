from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import MessageStates
from utils import get_main_keyboard, edit_or_send
from config import logger

router = Router()

from database import get_database
db = get_database()


@router.callback_query(F.data == "broadcast_message")
async def broadcast_message_start(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки"""
    # Получаем всех клиентов с Telegram ID (пока что функционал для будущего расширения)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        "📢 <b>Массовая рассылка</b>\n\n"
        "⚠️ <i>Внимание: сообщение будет отправлено всем пользователям бота</i>\n\n"
        "<b>Введите текст для рассылки:</b>",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.set_state(MessageStates.entering_broadcast_message)
    await callback.answer()


@router.message(MessageStates.entering_broadcast_message)
async def broadcast_message_execute(message: Message, state: FSMContext, bot: Bot):
    """Выполнение рассылки"""
    # Пока что отправляем только администраторам
    # В будущем здесь будет логика получения всех пользователей из БД
    
    from config import ADMIN_IDS
    
    text_to_send = f"📢 <b>РАССЫЛКА</b>\n\n{message.text}"
    
    success_count = 0
    fail_count = 0
    
    for user_id in ADMIN_IDS:
        if user_id == message.from_user.id:
            continue  # Не отправляем отправителю
        
        try:
            await bot.send_message(user_id, text_to_send, parse_mode='HTML')
            success_count += 1
            logger.info(f"Рассылка отправлена пользователю {user_id}")
        except Exception as e:
            fail_count += 1
            logger.error(f"Ошибка отправки рассылки пользователю {user_id}: {e}")
    
    await message.answer(
        f"📊 <b>Результат рассылки:</b>\n\n"
        f"✅ Отправлено: {success_count}\n"
        f"❌ Ошибок: {fail_count}",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    await state.clear()