import asyncio
import logging
from datetime import datetime, timedelta
from telegram.ext import ContextTypes
from database.repositories import UserRepository
from services.role_service import RoleService
from config.settings import settings

logger = logging.getLogger(__name__)

class ActivityService:
    def __init__(self):
        self.check_task = None
    
    async def start_activity_check(self, context: ContextTypes.DEFAULT_TYPE):
        """Запуск проверки активности"""
        if self.check_task is None or self.check_task.done():
            self.check_task = asyncio.create_task(
                self._activity_check_loop(context)
            )
    
    async def _activity_check_loop(self, context: ContextTypes.DEFAULT_TYPE):
        """Цикл проверки активности"""
        while True:
            try:
                await self.check_inactive_users(context)
                await asyncio.sleep(60)  # Проверка каждую минуту
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in activity check loop: {e}")
                await asyncio.sleep(60)
    
    async def check_inactive_users(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверка неактивных пользователей - БЕЗ УВЕДОМЛЕНИЙ"""
        try:
            inactive_users = await UserRepository.get_inactive_users(
                settings.ACTIVITY_TIMEOUT_MINUTES
            )
            
            for user in inactive_users:
                if user.role_assigned:
                    await RoleService.remove_role(
                        user_id=user.user_id,
                        chat_id=user.chat_id,
                        reason="inactivity",
                        context=context
                    )
                    
                    # Уведомление НЕ отправляем (по требованию задачи)
                    # Вместо этого только логируем
                    logger.info(f"Role removed from user {user.user_id} due to inactivity")
                    
        except Exception as e:
            logger.error(f"Error checking inactive users: {e}")
    
    async def update_user_activity(self, user_id: int):
        """Обновление активности пользователя"""
        try:
            user = await UserRepository.get_by_id(user_id)
            if user:
                user.last_activity = datetime.now()
                user.updated_at = datetime.now()
                await UserRepository.create_or_update(user)
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
    
    async def stop(self):
        """Остановка проверки активности"""
        if self.check_task and not self.check_task.done():
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
