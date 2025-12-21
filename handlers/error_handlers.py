import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.repositories import LogRepository
from database.models import LogEntry

logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    try:
        # Логируем ошибку
        error_msg = str(context.error)
        
        logger.error(f"Exception while handling an update: {error_msg}")
        
        # Сохраняем в лог базы данных
        user_id = update.effective_user.id if update and update.effective_user else 0
        await LogRepository.create(LogEntry(
            user_id=user_id,
            action="error",
            details=error_msg
        ))
        
        # Отправляем сообщение администратору
        if context.bot_data.get('admin_ids'):
            for admin_id in context.bot_data['admin_ids']:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"❌ Ошибка бота:\n\n{error_msg[:1000]}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send error to admin: {e}")
        
    except Exception as e:
        logger.error(f"Error in error handler: {e}")