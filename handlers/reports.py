import os
import csv
from io import StringIO
from datetime import datetime
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database
from states import ReportStates
from utils import get_main_keyboard, edit_or_send
from config import logger

router = Router()
db = Database()


@router.callback_query(F.data == "reports_menu")
async def reports_menu(callback: CallbackQuery):
    """Меню отчётов"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 База клиентов", callback_data="report_clients"))
    builder.row(InlineKeyboardButton(text="💰 Финансовый отчёт", callback_data="report_financial"))
    builder.row(InlineKeyboardButton(text="📊 История операций", callback_data="report_operations"))
    builder.row(InlineKeyboardButton(text="📥 Скачать CSV клиентов", callback_data="download_clients_csv"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    await edit_or_send(
        callback,
        "📈 <b>Отчёты и аналитика</b>\n\n"
        "Выберите тип отчёта:",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == "report_clients")
async def report_clients(callback: CallbackQuery, state: FSMContext):
    """Запрос отчёта по клиентам"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="reports_menu"))
    
    await edit_or_send(
        callback,
        "👥 <b>Отчёт по клиентам</b>\n\n"
        "<b>Введите период:</b>\n"
        "ГГГГ-ММ-ДД - ГГГГ-ММ-ДД\n\n"
        "Или отправьте '-' для отчёта за всё время",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.update_data(report_type='clients')
    await state.set_state(ReportStates.entering_date_range)
    await callback.answer()


@router.callback_query(F.data == "report_financial")
async def report_financial(callback: CallbackQuery, state: FSMContext):
    """Запрос финансового отчёта"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="reports_menu"))
    
    await edit_or_send(
        callback,
        "💰 <b>Финансовый отчёт</b>\n\n"
        "<b>Введите период:</b>\n"
        "ГГГГ-ММ-ДД - ГГГГ-ММ-ДД\n\n"
        "Или отправьте '-' для отчёта за всё время",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.update_data(report_type='financial')
    await state.set_state(ReportStates.entering_date_range)
    await callback.answer()


@router.callback_query(F.data == "report_operations")
async def report_operations(callback: CallbackQuery, state: FSMContext):
    """Запрос отчёта по операциям"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="reports_menu"))
    
    await edit_or_send(
        callback,
        "📊 <b>История операций</b>\n\n"
        "<b>Введите период:</b>\n"
        "ГГГГ-ММ-ДД - ГГГГ-ММ-ДД\n\n"
        "Или отправьте '-' для отчёта за всё время",
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await state.update_data(report_type='operations')
    await state.set_state(ReportStates.entering_date_range)
    await callback.answer()


@router.message(ReportStates.entering_date_range)
async def process_report_dates(message: Message, state: FSMContext):
    """Обработка дат для отчёта"""
    data = await state.get_data()
    report_type = data['report_type']
    
    start_date = None
    end_date = None
    
    if message.text != '-':
        try:
            parts = message.text.split()
            if len(parts) == 3:
                start_date = parts[0].strip()
                end_date = parts[2].strip()
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            else:
                await message.answer("❌ Неверный формат. Используйте: ГГГГ-ММ-ДД - ГГГГ-ММ-ДД")
                return
        except:
            await message.answer("❌ Неверный формат даты. Проверьте правильность ввода.")
            return
    
    if report_type == 'clients':
        await generate_clients_report(message, start_date, end_date)
    elif report_type == 'financial':
        await generate_financial_report(message, start_date, end_date)
    elif report_type == 'operations':
        await generate_operations_report(message, start_date, end_date)
    
    await state.clear()


async def generate_clients_report(message: Message, start_date: str = None, end_date: str = None):
    """Генерация отчёта по клиентам"""
    clients = db.get_clients_report(start_date, end_date)
    
    if not clients:
        await message.answer(
            "👥 <b>Отчёт по клиентам</b>\n\n"
            "❌ Нет данных за указанный период.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    period_text = "за всё время"
    if start_date and end_date:
        period_text = f"с {start_date} по {end_date}"
    
    text = f"👥 <b>БАЗА КЛИЕНТОВ</b>\n"
    text += f"📅 Период: {period_text}\n"
    text += f"📊 Всего клиентов: {len(clients)}\n\n"
    
    for client_name, phone, first_order, last_order, total_orders, total_spent in clients[:20]:
        text += f"👤 <b>{client_name}</b>\n"
        text += f"   📞 {phone}\n"
        text += f"   📅 Первый: {first_order[:10]}\n"
        text += f"   📅 Последний: {last_order[:10]}\n"
        text += f"   📦 Заказов: {total_orders}\n"
        if total_spent > 0:
            text += f"   💰 Сумма: {total_spent:.2f}\n"
        text += "\n"
    
    if len(clients) > 20:
        text += f"<i>... и ещё {len(clients) - 20} клиентов</i>"
    
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


async def generate_financial_report(message: Message, start_date: str = None, end_date: str = None):
    """Генерация финансового отчёта"""
    stats = db.get_financial_report(start_date, end_date)
    
    if not stats or stats[0] == 0:
        await message.answer(
            "💰 <b>Финансовый отчёт</b>\n\n"
            "❌ Нет данных за указанный период.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    total_bookings, total_revenue, avg_order = stats
    
    period_text = "за всё время"
    if start_date and end_date:
        period_text = f"с {start_date} по {end_date}"
    
    text = f"💰 <b>ФИНАНСОВЫЙ ОТЧЁТ</b>\n"
    text += f"📅 Период: {period_text}\n\n"
    text += f"📦 Всего бронирований: {total_bookings}\n"
    text += f"💵 Общая выручка: {total_revenue:.2f}\n"
    text += f"📊 Средний чек: {avg_order:.2f}\n"
    
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


async def generate_operations_report(message: Message, start_date: str = None, end_date: str = None):
    """Генерация отчёта по операциям"""
    operations = db.get_operations_report(start_date, end_date)
    
    if not operations:
        await message.answer(
            "📊 <b>История операций</b>\n\n"
            "❌ Нет операций за указанный период.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    period_text = "за всё время"
    if start_date and end_date:
        period_text = f"с {start_date} по {end_date}"
    
    active_count = sum(1 for op in operations if op[8] == 'active')
    completed_count = sum(1 for op in operations if op[8] == 'completed')
    
    text = f"📊 <b>ИСТОРИЯ ОПЕРАЦИЙ</b>\n"
    text += f"📅 Период: {period_text}\n"
    text += f"📈 Всего операций: {len(operations)}\n"
    text += f"✅ Активные: {active_count}\n"
    text += f"🏁 Завершённые: {completed_count}\n\n"
    
    for op in operations[:15]:
        booking_id, resource, client, phone, start, end, quantity, cost, status, created, completed = op
        
        status_emoji = "✅" if status == 'active' else "🏁"
        text += f"{status_emoji} <b>Бронь #{booking_id}</b>\n"
        text += f"   🎯 {resource} ({quantity} шт.)\n"
        text += f"   👤 {client} ({phone})\n"
        text += f"   📅 {start} — {end}\n"
        if cost:
            text += f"   💰 {cost}\n"
        text += f"   📝 {created[:16]}\n"
        if completed:
            text += f"   ✅ {completed[:16]}\n"
        text += "\n"
    
    if len(operations) > 15:
        text += f"<i>... и ещё {len(operations) - 15} операций</i>"
    
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode='HTML')


@router.callback_query(F.data == "download_clients_csv")
async def download_clients_csv(callback: CallbackQuery):
    """Скачивание CSV файла с клиентами"""
    clients = db.get_clients_report()
    
    if not clients:
        await callback.answer("❌ Нет данных для выгрузки", show_alert=True)
        return
    
    csv_content = StringIO()
    writer = csv.writer(csv_content)
    
    writer.writerow([
        'Имя клиента',
        'Телефон',
        'Первый заказ',
        'Последний заказ',
        'Всего заказов',
        'Общая сумма'
    ])
    
    for client in clients:
        writer.writerow(client)
    
    filename = f"clients_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        f.write(csv_content.getvalue())
    
    try:
        await callback.message.answer_document(
            FSInputFile(filename),
            caption=f"📊 <b>База клиентов</b>\nВсего записей: {len(clients)}",
            parse_mode='HTML'
        )
        os.remove(filename)
        await callback.answer("✅ Файл отправлен!")
    except Exception as e:
        logger.error(f"Ошибка отправки CSV: {e}")
        await callback.answer("❌ Ошибка при создании файла", show_alert=True)