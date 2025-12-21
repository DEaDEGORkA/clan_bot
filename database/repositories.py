import logging
from datetime import datetime, timedelta
from typing import List, Optional
from database.connection import Database
from database.models import User, ProfanityWord, LogEntry, RoleHistory

logger = logging.getLogger(__name__)

class UserRepository:
    @staticmethod
    async def create_or_update(user: User) -> bool:
        """Создание или обновление пользователя"""
        try:
            query = """
            INSERT INTO users (
                user_id, chat_id, username, first_name, last_name,
                nickname, role_assigned, is_blocked,
                last_activity, warnings_count, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                nickname = EXCLUDED.nickname,
                role_assigned = EXCLUDED.role_assigned,
                is_blocked = EXCLUDED.is_blocked,
                last_activity = EXCLUDED.last_activity,
                warnings_count = EXCLUDED.warnings_count,
                updated_at = EXCLUDED.updated_at
            """
            
            await Database.execute(
                query,
                user.user_id, user.chat_id, user.username, user.first_name,
                user.last_name, user.nickname, user.role_assigned, 
                user.is_blocked, user.last_activity, user.warnings_count,
                user.created_at, user.updated_at
            )
            return True
        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return False
    
    @staticmethod
    async def get_by_id(user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        try:
            query = "SELECT * FROM users WHERE user_id = $1"
            row = await Database.fetchrow(query, user_id)
            
            if row:
                user_dict = dict(row)
                return User(**user_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    @staticmethod
    async def get_by_chat_and_role(chat_id: int, role_assigned: Optional[bool] = None) -> List[User]:
        """Получение пользователей чата с ролью"""
        try:
            if role_assigned is None:
                query = "SELECT * FROM users WHERE chat_id = $1 ORDER BY last_activity DESC"
                rows = await Database.fetch(query, chat_id)
            else:
                query = """
                SELECT * FROM users 
                WHERE chat_id = $1 AND role_assigned = $2
                ORDER BY last_activity DESC
                """
                rows = await Database.fetch(query, chat_id, role_assigned)
            
            return [User(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting users by chat and role: {e}")
            return []
    
    @staticmethod
    async def get_inactive_users(timeout_minutes: int) -> List[User]:
        """Получение неактивных пользователей"""
        try:
            timeout = datetime.now() - timedelta(minutes=timeout_minutes)
            query = """
            SELECT * FROM users 
            WHERE role_assigned = TRUE 
            AND last_activity < $1
            """
            rows = await Database.fetch(query, timeout)
            return [User(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting inactive users: {e}")
            return []
    
    @staticmethod
    async def delete(user_id: int) -> bool:
        """Удаление пользователя"""
        try:
            query = "DELETE FROM users WHERE user_id = $1"
            await Database.execute(query, user_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

class ProfanityWordRepository:
    @staticmethod
    async def get_all() -> List[str]:
        """Получение всех матных слов"""
        try:
            query = "SELECT word FROM profanity_words ORDER BY word"
            rows = await Database.fetch(query)
            return [row['word'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting profanity words: {e}")
            return []
    
    @staticmethod
    async def add_word(word: str) -> bool:
        """Добавление матного слова"""
        try:
            query = "INSERT INTO profanity_words (word) VALUES ($1) ON CONFLICT (word) DO NOTHING"
            await Database.execute(query, word)
            return True
        except Exception as e:
            logger.error(f"Error adding profanity word: {e}")
            return False
    
    @staticmethod
    async def add_words(words: List[str]) -> bool:
        """Добавление нескольких матных слов"""
        try:
            for word in words:
                await ProfanityWordRepository.add_word(word)
            return True
        except Exception as e:
            logger.error(f"Error adding profanity words: {e}")
            return False
    
    @staticmethod
    async def delete_word(word: str) -> bool:
        """Удаление матного слова"""
        try:
            query = "DELETE FROM profanity_words WHERE word = $1"
            await Database.execute(query, word)
            return True
        except Exception as e:
            logger.error(f"Error deleting profanity word: {e}")
            return False
    
    @staticmethod
    async def clear_all() -> bool:
        """Очистка всех матных слов"""
        try:
            query = "DELETE FROM profanity_words"
            await Database.execute(query)
            return True
        except Exception as e:
            logger.error(f"Error clearing profanity words: {e}")
            return False

class LogRepository:
    @staticmethod
    async def create(log_entry: LogEntry) -> bool:
        """Создание записи лога"""
        try:
            query = """
            INSERT INTO logs (user_id, action, details, created_at)
            VALUES ($1, $2, $3, $4)
            """
            await Database.execute(
                query,
                log_entry.user_id, log_entry.action, 
                log_entry.details, log_entry.created_at
            )
            return True
        except Exception as e:
            logger.error(f"Error creating log: {e}")
            return False
    
    @staticmethod
    async def get_by_user(user_id: int, limit: int = 50) -> List[LogEntry]:
        """Получение логов пользователя"""
        try:
            query = """
            SELECT * FROM logs 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT $2
            """
            rows = await Database.fetch(query, user_id, limit)
            return [LogEntry(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting logs by user: {e}")
            return []
    
    @staticmethod
    async def get_recent(limit: int = 100) -> List[LogEntry]:
        """Получение последних логов"""
        try:
            query = """
            SELECT * FROM logs 
            ORDER BY created_at DESC 
            LIMIT $1
            """
            rows = await Database.fetch(query, limit)
            return [LogEntry(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting recent logs: {e}")
            return []

class RoleHistoryRepository:
    @staticmethod
    async def create(role_history: RoleHistory) -> bool:
        """Создание записи истории ролей"""
        try:
            query = """
            INSERT INTO role_history (user_id, role_name, assigned_at, removed_at, reason)
            VALUES ($1, $2, $3, $4, $5)
            """
            await Database.execute(
                query,
                role_history.user_id, role_history.role_name,
                role_history.assigned_at, role_history.removed_at,
                role_history.reason
            )
            return True
        except Exception as e:
            logger.error(f"Error creating role history: {e}")
            return False
    
    @staticmethod
    async def update_removal(history_id: int, removed_at: datetime, reason: str = None) -> bool:
        """Обновление записи о снятии роли"""
        try:
            query = """
            UPDATE role_history 
            SET removed_at = $1, reason = $2 
            WHERE history_id = $3
            """
            await Database.execute(query, removed_at, reason, history_id)
            return True
        except Exception as e:
            logger.error(f"Error updating role removal: {e}")
            return False
    
    @staticmethod
    async def get_by_user_id(user_id: int) -> List[RoleHistory]:
        """Получение истории ролей пользователя"""
        try:
            query = """
            SELECT * FROM role_history 
            WHERE user_id = $1 
            ORDER BY assigned_at DESC
            """
            rows = await Database.fetch(query, user_id)
            return [RoleHistory(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting role history by user_id: {e}")
            return []
    
    @staticmethod
    async def update(role_history: RoleHistory) -> bool:
        """Обновление записи истории ролей"""
        try:
            query = """
            UPDATE role_history 
            SET removed_at = $1, reason = $2 
            WHERE history_id = $3
            """
            await Database.execute(
                query,
                role_history.removed_at,
                role_history.reason,
                role_history.history_id
            )
            return True
        except Exception as e:
            logger.error(f"Error updating role history: {e}")
            return False