import logging
import asyncio
from datetime import datetime
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, MessageHandler, filters, ChatMemberHandler, CommandHandler
from database.repositories import UserRepository, LogRepository
from database.models import User, LogEntry
from services.role_service import RoleService, delete_message_after_delay
from services.activity_service import ActivityService
from services.profanity_filter import ProfanityFilter
from config.settings import settings

logger = logging.getLogger(__name__)

class UserHandlers:
    def __init__(self, activity_service: ActivityService, profanity_filter: ProfanityFilter):
        self.activity_service = activity_service
        self.profanity_filter = profanity_filter
    
    async def handle_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка новых участников"""
        try:
            chat_member = update.chat_member
            
            # Проверяем, что это действительно новое присоединение
            if (chat_member.new_chat_member.status == 'member' and 
                chat_member.old_chat_member.status not in ['member', 'restricted']):
                
                user = chat_member.new_chat_member.user
                chat_id = update.effective_chat.id
                
                # Пропускаем бота
                if user.id == context.bot.id:
                    return
                
                logger.info(f"New member joined: {user.id} ({user.username or user.first_name})")
                
                # Получаем пользователя из базы
                db_user = await UserRepository.get_by_id(user.id)
                
                if not db_user:
                    # Создаем нового пользователя
                    db_user = User(
                        user_id=user.id,
                        chat_id=chat_id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        nickname=None,
                        last_activity=datetime.now(),
                        warnings_count=0
                    )
                    await UserRepository.create_or_update(db_user)
                    
                    # Отправляем приветственное сообщение
                    try:
                        welcome_msg = await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🖐 Добро пожаловать, {user.mention_html()}!",
                            parse_mode="HTML"
                        )
                        # Удаляем через 5 секунд
                        asyncio.create_task(delete_message_after_delay(context, chat_id, welcome_msg.message_id))
                    except Exception as e:
                        logger.error(f"Failed to send welcome message: {e}")
                    
                    # Логируем
                    await LogRepository.create(LogEntry(
                        user_id=user.id,
                        action="new_member",
                        details="User joined the chat"
                    ))
                    
                    logger.info(f"Created new user record for {user.id}")
                    
                else:
                    # Пользователь уже есть в базе
                    logger.info(f"Existing user rejoined: {user.id} ({user.username or user.first_name})")
                    
                    # Обновляем chat_id на случай, если он изменился
                    db_user.chat_id = chat_id
                    db_user.last_activity = datetime.now()
                    await UserRepository.create_or_update(db_user)
                    
                    # Если у пользователя уже есть nickname, пытаемся восстановить роль
                    if db_user.nickname and not db_user.role_assigned:
                        logger.info(f"Restoring role for user {user.id} with nickname '{db_user.nickname}'")
                        success = await RoleService.assign_role(
                            user_id=user.id,
                            chat_id=chat_id,
                            nickname=db_user.nickname,
                            context=context
                        )
                        
                        if success:
                            logger.info(f"Successfully restored role for user {user.id}")
                        else:
                            logger.warning(f"Could not restore role for user {user.id}")
                    
        except Exception as e:
            logger.error(f"Error in handle_new_member: {e}")
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выхода пользователя из чата"""
        try:
            chat_member = update.chat_member
            
            # Проверяем, что пользователь вышел
            if (chat_member.new_chat_member.status in ['left', 'kicked'] and 
                chat_member.old_chat_member.status == 'member'):
                
                user = chat_member.new_chat_member.user
                user_id = user.id
                chat_id = update.effective_chat.id
                
                logger.info(f"User left: {user_id} ({user.username or user.first_name})")
                
                # Снимаем роль без уведомления
                await RoleService.remove_role(
                    user_id=user_id,
                    chat_id=chat_id,
                    reason="left_chat",
                    context=context
                )
                
                # Логируем
                await LogRepository.create(LogEntry(
                    user_id=user_id,
                    action="member_left",
                    details="User left the chat"
                ))
                
        except Exception as e:
            logger.error(f"Error in handle_left_member: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщений в группе"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        logger.debug(f"Message from user {user_id}: {message_text[:50]}...")
        
        # Обновляем активность
        await self.activity_service.update_user_activity(user_id)
        
        # Получаем пользователя
        user = await UserRepository.get_by_id(user_id)
        if not user:
            # Если пользователя нет в БД, создаем
            user = User(
                user_id=user_id,
                chat_id=chat_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name,
                last_activity=datetime.now(),
                warnings_count=0
            )
            await UserRepository.create_or_update(user)
            logger.info(f"Created user record for {user_id}")
        else:
            # Обновляем последнюю активность
            user.last_activity = datetime.now()
            await UserRepository.create_or_update(user)
            
            # Если у пользователя есть nickname, но роль не назначена - пытаемся восстановить
            # Только если пользователь не заблокирован
            if user.nickname and not user.role_assigned and not user.is_blocked:
                logger.info(f"Restoring role for active user {user_id} with nickname '{user.nickname}'")
                success = await RoleService.assign_role(
                    user_id=user_id,
                    chat_id=chat_id,
                    nickname=user.nickname,
                    context=context
                )
                
                if success:
                    logger.info(f"Successfully restored role for user {user_id}")
                else:
                    logger.warning(f"Could not restore role for user {user_id} - check bot admin rights")
        
        # Проверяем на матные слова
        if message_text and self.profanity_filter.contains_profanity(message_text):
            logger.info(f"Profanity detected in message from user {user_id}")
            
            # Удаляем сообщение с матом
            try:
                await update.message.delete()
                logger.info(f"Deleted profane message from user {user_id}")
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
            
            # Увеличиваем счетчик предупреждений (для статистики, но не блокируем)
            user.warnings_count += 1
            await UserRepository.create_or_update(user)
            
            # Отправляем предупреждение
            warning_text = f"⚠️ {update.effective_user.mention_html()}, пожалуйста, не используйте ненормативную лексику!"
            
            try:
                warning_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=warning_text,
                    parse_mode="HTML"
                )
                # Удаляем предупреждение через 5 секунд
                asyncio.create_task(delete_message_after_delay(context, chat_id, warning_msg.message_id))
                logger.info(f"Sent profanity warning to user {user_id} (warning #{user.warnings_count})")
            except Exception as e:
                logger.error(f"Failed to send profanity warning: {e}")
            
            # Логируем
            await LogRepository.create(LogEntry(
                user_id=user_id,
                action="profanity_warning",
                details=f"Message contained profanity: {message_text[:100]}"
            ))
    
    async def handle_changenick_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /changenick - изменение должности"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        logger.info(f"User {user_id} requested nickname change")
        
        # Проверяем аргументы команды
        if not context.args:
            help_msg = await update.message.reply_text(
                "Использование: /changenick <новый_никнейм>\n"
                "Пример: /changenick Старший_воин\n\n"
                "📝 Или просто введите новый никнейм в ответ на это сообщение."
            )
            # Удаляем через 5 секунд
            asyncio.create_task(delete_message_after_delay(context, chat_id, help_msg.message_id))
            return
        
        new_nickname = ' '.join(context.args)
        
        # Проверяем длину никнейма
        if len(new_nickname) > 16:
            error_msg = await update.message.reply_text(
                "❌ Никнейм слишком длинный (максимум 16 символов)."
            )
            asyncio.create_task(delete_message_after_delay(context, chat_id, error_msg.message_id))
            return
        
        # Получаем пользователя или создаем, если его нет в БД
        user = await UserRepository.get_by_id(user_id)
        if not user:
            # Если пользователя нет в БД, создаем его
            logger.info(f"User {user_id} not found in DB, creating new record")
            user = User(
                user_id=user_id,
                chat_id=chat_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name,
                nickname=None,
                last_activity=datetime.now(),
                warnings_count=0
            )
            await UserRepository.create_or_update(user)
            logger.info(f"Created user record for {user_id} in changenick command")
        
        # Назначаем роль (это также обновит никнейм и назначит админа)
        logger.info(f"Attempting to assign role for user {user_id} with nickname '{new_nickname}'")
        role_success = await RoleService.assign_role(
            user_id=user_id,
            chat_id=chat_id,
            nickname=new_nickname,
            context=context
        )
        
        if role_success:
            logger.info(f"Role successfully assigned for user {user_id}")
            # Отправляем подтверждение
            success_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Должность '{new_nickname}' установлена для {update.effective_user.mention_html()}",
                parse_mode="HTML"
            )
            asyncio.create_task(delete_message_after_delay(context, chat_id, success_msg.message_id))
        else:
            logger.warning(f"Role assignment failed for user {user_id}")
            error_msg = await update.message.reply_text(
                "❌ Не удалось установить должность. Проверьте, что бот имеет права администратора."
            )
            asyncio.create_task(delete_message_after_delay(context, chat_id, error_msg.message_id))
    
    def get_handlers(self):
        """Получение всех обработчиков пользователей"""
        return [
            ChatMemberHandler(self.handle_new_member, ChatMemberHandler.CHAT_MEMBER),
            ChatMemberHandler(self.handle_left_member, ChatMemberHandler.CHAT_MEMBER),
            CommandHandler("changenick", self.handle_changenick_command),
            CommandHandler("cn", self.handle_changenick_command),  # Алиас для быстрого доступа
            MessageHandler(filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND, self.handle_message)
        ]
