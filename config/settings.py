import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def parse_admin_ids(admin_ids_str: str) -> List[int]:
    """Парсинг строки с ID администраторов"""
    if not admin_ids_str:
        return []
    
    try:
        admin_ids_str = admin_ids_str.strip().strip('"').strip("'")
        if not admin_ids_str:
            return []
        
        admin_ids = []
        for admin_id in admin_ids_str.split(','):
            admin_id = admin_id.strip()
            if admin_id:
                admin_ids.append(int(admin_id))
        return admin_ids
    except Exception as e:
        logger.error(f"Error parsing ADMIN_IDS '{admin_ids_str}': {e}")
        return []

class Settings:
    """Настройки приложения"""
    
    def __init__(self):
        # Telegram
        self.BOT_TOKEN = os.getenv('BOT_TOKEN', '')
        self.ADMIN_IDS = parse_admin_ids(os.getenv('ADMIN_IDS', ''))
        self.BOT_USERNAME = os.getenv('BOT_USERNAME', '')
        self.CHAT_ID = self._parse_chat_id(os.getenv('CHAT_ID'))
        
        # Database
        self.DB_HOST = os.getenv('DB_HOST', 'localhost')
        self.DB_PORT = int(os.getenv('DB_PORT', '5432'))
        self.DB_NAME = os.getenv('DB_NAME', 'telegram_bot_db')
        self.DB_USER = os.getenv('DB_USER', 'postgres')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        self.DB_SSL_MODE = os.getenv('DB_SSL_MODE', 'disable')
        
        # Application
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.ACTIVITY_TIMEOUT_MINUTES = int(os.getenv('ACTIVITY_TIMEOUT_MINUTES', '5'))
        self.MESSAGE_DELETE_DELAY = 5  # Секунды для удаления сообщений
        
        # Список матных слов (можно вынести в отдельный файл)
        self.PROFANITY_WORDS = [
            'хуй', 'блять', 'пизда', 'блядь',  # Замените на реальные слова
            'badword1', 'badword2'
        ]
        
        # Пути
        self.LOG_DIR = os.getenv('LOG_DIR', 'logs')
        
        # Валидация
        self._validate()
    
    def _parse_chat_id(self, chat_id_str: Optional[str]) -> Optional[int]:
        """Парсинг CHAT_ID из строки в целое число"""
        if not chat_id_str:
            return None
        
        try:
            # Убираем пробелы и преобразуем в int
            return int(chat_id_str.strip())
        except (ValueError, TypeError):
            logger.warning(f"Invalid CHAT_ID format: {chat_id_str}. Should be integer.")
            return None
    
    def _validate(self):
        """Проверка обязательных полей"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        logger.info(f"Settings loaded: ADMIN_IDS={self.ADMIN_IDS}, CHAT_ID={self.CHAT_ID}")

settings = Settings()
