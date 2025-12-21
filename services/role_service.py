import logging
import asyncio
from datetime import datetime
from telegram import ChatPermissions
from telegram.ext import ContextTypes
from database.repositories import UserRepository, RoleHistoryRepository, LogRepository
from database.models import RoleHistory, LogEntry
from config.settings import settings

logger = logging.getLogger(__name__)

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 5):
    """Удаление сообщения через указанное время"""
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Failed to delete message: {e}")

class RoleService:
    @staticmethod
    async def is_user_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверка, является ли пользователь администратором чата"""
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            return chat_member.status in ['administrator', 'creator']
        except Exception as e:
            logger.error(f"Failed to check admin status for user {user_id}: {e}")
            return False

    @staticmethod
    async def _ensure_bot_is_admin(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверка, является ли бот администратором с нужными правами"""
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            
            # Проверяем, что бот - администратор
            if bot_member.status not in ['administrator', 'creator']:
                logger.error(f"Bot is not an admin in chat {chat_id}")
                return False
            
            # Проверяем право назначать администраторов
            if not bot_member.can_promote_members:
                logger.error(f"Bot doesn't have permission to promote members in chat {chat_id}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to check bot admin status: {e}")
            return False

    @staticmethod
    async def _set_custom_title_with_retry(
        chat_id: int,
        user_id: int,
        nickname: str,
        context: ContextTypes.DEFAULT_TYPE,
        max_retries: int = 3,
        delay: float = 1.0
    ) -> bool:
        """Установка кастомного заголовка с повторными попытками"""
        for attempt in range(max_retries):
            try:
                await context.bot.set_chat_administrator_custom_title(
                    chat_id=chat_id,
                    user_id=user_id,
                    custom_title=nickname[:16]
                )
                logger.info(f"Successfully set custom title '{nickname[:16]}' for user {user_id} (attempt {attempt + 1})")
                return True
            except Exception as e:
                if "User is not an administrator" in str(e):
                    logger.warning(f"User {user_id} is not an admin yet, waiting... (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        continue
                logger.error(f"Failed to set custom title for user {user_id}: {e}")
                return False
        return False

    @staticmethod
    async def assign_role(
        user_id: int,
        chat_id: int,
        nickname: str,
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Назначение роли пользователю"""
        try:
            # Получаем пользователя
            user = await UserRepository.get_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found in database")
                return False
            
            # Проверяем, является ли бот администратором с нужными правами
            if not await RoleService._ensure_bot_is_admin(chat_id, context):
                logger.warning(f"Bot can't promote members in chat {chat_id}, only saving nickname in DB")
                # Сохраняем только никнейм в БД без назначения прав
                user.nickname = nickname
                user.role_assigned = False  # Не назначаем права
                user.updated_at = datetime.now()
                await UserRepository.create_or_update(user)
                return True
            
            # Проверяем, является ли пользователь уже администратором
            is_admin = await RoleService.is_user_admin(chat_id, user_id, context)
            
            if not is_admin:
                # Назначаем пользователя администратором с ограниченными правами
                try:
                    # Только основные права для работы
                    await context.bot.promote_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        can_post_messages=True,       # Может отправлять сообщения
                        can_edit_messages=False,
                        can_delete_messages=False,
                        can_restrict_members=False,
                        can_promote_members=False,
                        can_change_info=False,
                        can_pin_messages=False,
                        can_manage_chat=False,
                        can_manage_video_chats=False,
                        can_invite_users=False,
                        is_anonymous=False
                    )
                    logger.info(f"Successfully promoted user {user_id} to admin with limited rights")
                    
                    # Ждем 2 секунды для обновления статуса в Telegram
                    await asyncio.sleep(2)
                    
                except Exception as promote_error:
                    logger.error(f"Failed to promote user {user_id}: {promote_error}")
                    
                    # Если не удалось назначить администратором, сохраняем только никнейм
                    user.nickname = nickname
                    user.role_assigned = False
                    user.updated_at = datetime.now()
                    await UserRepository.create_or_update(user)
                    return True
            
            # Обновляем информацию о пользователе после назначения прав
            is_admin = await RoleService.is_user_admin(chat_id, user_id, context)
            
            # Обновляем пользователя
            user.role_assigned = True
            user.nickname = nickname
            user.updated_at = datetime.now()
            await UserRepository.create_or_update(user)
            
            # Пытаемся установить кастомный заголовок с повторными попытками
            if is_admin:
                title_success = await RoleService._set_custom_title_with_retry(
                    chat_id=chat_id,
                    user_id=user_id,
                    nickname=nickname,
                    context=context,
                    max_retries=3,
                    delay=2.0
                )
                if not title_success:
                    logger.warning(f"Could not set custom title for user {user_id}, but role is assigned")
            else:
                logger.warning(f"User {user_id} is still not an admin after promotion, skipping title")
            
            # Логируем
            await LogRepository.create(LogEntry(
                user_id=user_id,
                action="role_assigned",
                details=f"Role '{nickname}' assigned"
            ))
            
            # Сохраняем в историю
            await RoleHistoryRepository.create(RoleHistory(
                user_id=user_id,
                role_name=nickname,
                assigned_at=datetime.now()
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role to user {user_id}: {e}")
            await LogRepository.create(LogEntry(
                user_id=user_id,
                action="role_assignment_error",
                details=str(e)
            ))
            return False
    
    @staticmethod
    async def remove_role(
        user_id: int,
        chat_id: int,
        reason: str = "inactivity",
        context: ContextTypes.DEFAULT_TYPE = None
    ) -> bool:
        """Снятие роли с пользователя"""
        try:
            # Получаем пользователя
            user = await UserRepository.get_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found when trying to remove role")
                return False
            
            if not user.role_assigned:
                logger.info(f"User {user_id} doesn't have role assigned, skipping")
                return True  # Уже не имеет роли
            
            # Проверяем, является ли пользователь администратором, прежде чем снимать права
            if context and await RoleService.is_user_admin(chat_id, user_id, context):
                try:
                    # Снимаем права администратора
                    await context.bot.promote_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        can_post_messages=False,
                        can_edit_messages=False,
                        can_delete_messages=False,
                        can_restrict_members=False,
                        can_promote_members=False,
                        can_change_info=False,
                        can_pin_messages=False,
                        can_manage_chat=False,
                        can_manage_video_chats=False,
                        can_invite_users=False
                    )
                    logger.info(f"Successfully demoted user {user_id} in chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to demote user {user_id}: {e}")
                    # Продолжаем, даже если не удалось снять права
            else:
                logger.info(f"User {user_id} is not an admin or no context provided, skipping demotion")
            
            # Обновляем пользователя
            user.role_assigned = False
            user.updated_at = datetime.now()
            await UserRepository.create_or_update(user)
            
            # Обновляем историю ролей
            try:
                # Находим последнюю активную роль пользователя
                role_history_list = await RoleHistoryRepository.get_by_user_id(user_id)
                for role_history in role_history_list:
                    if not role_history.removed_at:
                        role_history.removed_at = datetime.now()
                        role_history.reason = reason
                        await RoleHistoryRepository.update(role_history)
            except Exception as e:
                logger.error(f"Failed to update role history: {e}")
            
            # Логируем
            await LogRepository.create(LogEntry(
                user_id=user_id,
                action="role_removed",
                details=f"Role removed: {reason}"
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing role from user {user_id}: {e}")
            await LogRepository.create(LogEntry(
                user_id=user_id,
                action="role_removal_error",
                details=str(e)
            ))
            return False
    
    @staticmethod
    async def update_nickname(
        user_id: int,
        chat_id: int,
        new_nickname: str,
        context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """Обновление никнейма пользователя"""
        try:
            # Получаем пользователя
            user = await UserRepository.get_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found when updating nickname")
                return False
            
            old_nickname = user.nickname or "Без роли"
            
            # Обновляем никнейм в базе данных
            user.nickname = new_nickname
            user.updated_at = datetime.now()
            await UserRepository.create_or_update(user)
            
            # Пытаемся обновить кастомный заголовок с повторными попытками
            if await RoleService.is_user_admin(chat_id, user_id, context):
                title_success = await RoleService._set_custom_title_with_retry(
                    chat_id=chat_id,
                    user_id=user_id,
                    nickname=new_nickname,
                    context=context,
                    max_retries=3,
                    delay=2.0
                )
                if title_success:
                    logger.info(f"Updated custom title for user {user_id} to '{new_nickname[:16]}'")
                else:
                    logger.warning(f"Failed to update custom title for user {user_id}")
            else:
                logger.info(f"User {user_id} is not an administrator, saving nickname in DB only")
            
            # Логируем
            await LogRepository.create(LogEntry(
                user_id=user_id,
                action="nickname_updated",
                details=f"From '{old_nickname}' to '{new_nickname}'"
            ))
            
            # Отправляем сообщение об обновлении
            try:
                msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✏️ Никнейм изменен с '{old_nickname}' на '{new_nickname}'"
                )
                # Удаляем через 5 секунд
                asyncio.create_task(delete_message_after_delay(context, chat_id, msg.message_id))
            except Exception as e:
                logger.error(f"Failed to send nickname update message: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating nickname for user {user_id}: {e}")
            return False
