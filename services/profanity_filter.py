import re
import logging
from typing import List
from database.repositories import ProfanityWordRepository

logger = logging.getLogger(__name__)

class ProfanityFilter:
    """Фильтр нецензурной лексики"""
    
    def __init__(self):
        self.bad_words = []
        self.pattern = None
    
    async def load_words(self):
        """Загрузка матных слов из базы данных"""
        try:
            self.bad_words = await ProfanityWordRepository.get_all()
            self._update_pattern()
            
            if not self.bad_words:
                logger.warning("No profanity words loaded from database - filter will not work!")
            else:
                logger.info(f"Profanity filter loaded {len(self.bad_words)} words")
                logger.debug(f"Sample words (first 5): {self.bad_words[:5]}")
                
        except Exception as e:
            logger.error(f"Failed to load profanity words from database: {e}")
            self.bad_words = []
            self.pattern = None
    
    def _update_pattern(self):
        """Обновление регулярного выражения"""
        if self.bad_words:
            try:
                # Экранируем специальные символы в словах и приводим к нижнему регистру
                escaped_words = [re.escape(word.lower()) for word in self.bad_words]
                # Создаем паттерн для поиска слов целиком
                # Используем универсальный подход для границ слов (работает с кириллицей и латиницей)
                # Граница слова: начало строки, пробел, пунктуация, или не буква/цифра перед словом
                # и конец строки, пробел, пунктуация, или не буква/цифра после слова
                # \W соответствует не-словесным символам, но не работает с кириллицей, поэтому используем [^\w]
                pattern_str = r'(?:^|[^\w])(' + '|'.join(escaped_words) + r')(?:[^\w]|$)'
                self.pattern = re.compile(pattern_str, re.IGNORECASE | re.UNICODE)
                logger.debug(f"Created regex pattern with {len(self.bad_words)} words")
            except Exception as e:
                logger.error(f"Error creating regex pattern: {e}")
                self.pattern = None
        else:
            self.pattern = None
            logger.warning("No bad words to create pattern from")
    
    def contains_profanity(self, text: str) -> bool:
        """Проверка на наличие матных слов"""
        if not text:
            return False
        
        if not self.pattern:
            logger.warning("Profanity pattern is None - filter not initialized")
            return False
        
        try:
            # Приводим текст к нижнему регистру для поиска
            text_lower = text.lower()
            
            # Проверяем через регулярное выражение
            result = bool(self.pattern.search(text_lower))
            
            # Дополнительная проверка: ищем слова как подстроки (на случай если regex не сработал)
            if not result:
                # Проверяем каждое слово отдельно
                for word in self.bad_words:
                    word_lower = word.lower()
                    # Ищем слово как отдельное слово (окруженное не-буквами или границами)
                    if re.search(r'(?:^|[^\w])' + re.escape(word_lower) + r'(?:[^\w]|$)', text_lower, re.IGNORECASE | re.UNICODE):
                        result = True
                        logger.debug(f"Found profanity word '{word}' in text (fallback check)")
                        break
            
            if result:
                # Находим и логируем совпадения
                matches = self.pattern.findall(text_lower) if self.pattern else []
                logger.info(f"Profanity detected: found {len(matches) if matches else 1} matches in text")
                logger.debug(f"Matched words: {matches}")
                logger.debug(f"Original text: {text[:100]}...")
            
            return result
        except Exception as e:
            logger.error(f"Error checking profanity in text: {e}")
            return False
    
    async def reload_words(self):
        """Перезагрузка списка матных слов из базы"""
        await self.load_words()
    
    def get_profanity_count(self, text: str) -> int:
        """Подсчет количества матных слов в тексте"""
        if not text or not self.pattern:
            return 0
        
        try:
            matches = self.pattern.findall(text.lower())
            return len(matches)
        except Exception as e:
            logger.error(f"Error counting profanity: {e}")
            return 0
