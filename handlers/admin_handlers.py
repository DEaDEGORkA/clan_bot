import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters
from database.repositories import UserRepository, LogRepository
from services.role_service import RoleService
from config.settings import settings

logger = logging.getLogger(__name__)

class AdminHandlers:
    def __init__(self):
        pass
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in settings.ADMIN_IDS
    
    async def unblock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /unblock - разблокировка пользователя"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            return
        
        if not context.args:
            await update.message.reply_text("Использование: /unblock @username или /unblock user_id")
            return
        
        target = context.args[0]
        chat_id = update.effective_chat.id
        
        try:
            if target.startswith('@'):
                # TODO: реализовать поиск по username
                await update.message.reply_text("Пожалуйста, используйте ID пользователя.")
                return
            
            target_id = int(target)
            
            # Разблокируем пользователя
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                permissions=None  # Сбрасываем ограничения
            )
            
            # Обновляем пользователя в базе
            user = await UserRepository.get_by_id(target_id)
            if user:
                user.is_blocked = False
                user.warnings_count = 0
                await UserRepository.create_or_update(user)
            
            await update.message.reply_text(f"✅ Пользователь {target_id} разблокирован.")
            
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ID пользователя.")
        except Exception as e:
            logger.error(f"Error in unblock command: {e}")
            await update.message.reply_text("❌ Произошла ошибка.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            return
        
        chat_id = update.effective_chat.id
        
        try:
            # Получаем пользователей с ролью
            users_with_roles = await UserRepository.get_by_chat_and_role(chat_id, True)
            all_users = await UserRepository.get_by_chat_and_role(chat_id, None)
            
            message = "📊 Статистика:\n\n"
            message += f"👥 Всего пользователей: {len(all_users)}\n"
            message += f"🎭 С активными ролями: {len(users_with_roles)}\n"
            message += f"⏱️ Таймаут неактивности: {settings.ACTIVITY_TIMEOUT_MINUTES} мин\n"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики.")
    
    def get_handlers(self):
        """Получение всех обработчиков администраторов"""
        return [
            CommandHandler("unblock", self.unblock_command, filters=filters.ChatType.GROUPS),
            CommandHandler("stats", self.stats_command, filters=filters.ChatType.GROUPS)
        ]
