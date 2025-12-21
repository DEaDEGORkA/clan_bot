#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import Database
from database.repositories import ProfanityWordRepository
from services.profanity_filter import ProfanityFilter

async def test_profanity():
    """Тест фильтра матных слов"""
    # Подключаемся к базе данных
    await Database.create_pool()
    
    # Создаем фильтр
    filter = ProfanityFilter()
    await filter._load_words()
    
    print(f"Загружено слов: {len(filter.bad_words)}")
    print(f"Слова: {filter.bad_words}")
    
    # Тестовые сообщения
    test_messages = [
        "Привет как дела",
        "Это плохоеслово1 сообщение",
        "плохоеслово2 и еще текст",
        "Нормальное сообщение",
        "Оскорбление1 здесь",
        "Мама мыла раму"
    ]
    
    for msg in test_messages:
        contains = filter.contains_profanity(msg)
        print(f"'{msg}' -> содержит мат: {contains}")
        if contains:
            censored = filter.censor_text(msg)
            print(f"  Цензурировано: {censored}")
    
    # Добавим тестовое слово
    print("\nДобавляем тестовое слово 'тестмат'...")
    await ProfanityWordRepository.add_word("тестмат")
    
    # Перезагружаем фильтр
    await filter.reload_words()
    print(f"Теперь загружено слов: {len(filter.bad_words)}")
    
    # Тестируем снова
    test_msg = "Сообщение с тестмат словом"
    print(f"'{test_msg}' -> содержит мат: {filter.contains_profanity(test_msg)}")
    
    await Database.close_pool()

if __name__ == "__main__":
    asyncio.run(test_profanity())
