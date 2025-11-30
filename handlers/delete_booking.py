from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from utils import get_main_keyboard, edit_or_send, format_booking

router = Router()
db = Database()


@router.callback_query(F.data == "delete_booking_menu")
async def delete_booking_menu(callback: CallbackQuery):
    """Меню удаления бронирования"""
    bookings = db.get_all_active_bookings()
    
    if not bookings:
        await edit_or_send(
            callback,
            "🗑️ <b>Удаление брони</b>\n\n"
            "❌ Активных броней не найдено.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        await callback.answer()
        return
    
    text = f"🗑️ <b>Удаление брони</b>\n"
    text += f"📊 Активных броней: {len(bookings)}\n\n"
    text += "Выберите бронь для удаления:"
    
    builder = InlineKeyboardBuilder()
    for booking in bookings[:10]:
        booking_id, resource, client, _, start, end, quantity = booking[:7]
        builder.row(InlineKeyboardButton(
            text=f"#{booking_id} | {resource} ({quantity} шт.) | {client}",
            callback_data=f"delbooking_{booking_id}"
        ))
    
    if len(bookings) > 10:
        text += f"\n<i>Показаны первые 10 из {len(bookings)} броней</i>"
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("delbooking_"))
async def delete_booking_confirm(callback: CallbackQuery):
    """Подтверждение удаления брони"""
    booking_id = int(callback.data.split("_")[1])
    
    booking = db.get_booking_details(booking_id)
    if not booking:
        await callback.answer("❌ Бронь не найдена", show_alert=True)
        return
    
    text = "⚠️ <b>Подтверждение удаления</b>\n\n"
    text += "Вы уверены, что хотите удалить эту бронь?\n\n"
    text += format_booking(booking)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirmdel_{booking_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="delete_booking_menu")
    )
    
    await edit_or_send(callback, text, reply_markup=builder.as_markup(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith("confirmdel_"))
async def delete_booking_execute(callback: CallbackQuery):
    """Выполнение удаления брони"""
    booking_id = int(callback.data.split("_")[1])
    
    if db.delete_booking(booking_id):
        await callback.answer(f"✅ Бронь #{booking_id} удалена!", show_alert=True)
        await edit_or_send(
            callback,
            f"✅ <b>Бронь #{booking_id} успешно удалена!</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)