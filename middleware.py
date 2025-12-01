from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

from config import is_admin, logger


class AdminCheckMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем команду /start для логирования попыток доступа
        if isinstance(event, Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)
        
        # Проверяем права администратора
        user_id = event.from_user.id
        if not is_admin(user_id):
            logger.warning(f"Попытка доступа от неавторизованного пользователя: {user_id}")
            
            if isinstance(event, Message):
                await event.answer("⛔ У вас нет доступа к этому боту.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ У вас нет доступа", show_alert=True)
            
            return
        
        # Пользователь - администратор, продолжаем обработку
        return await handler(event, data)