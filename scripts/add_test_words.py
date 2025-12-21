#!/usr/bin/env python3
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import Database
from database.repositories import ProfanityWordRepository

async def add_test_words():
    await Database.create_pool()
    
    # Тестовые матные слова (замените на реальные)
    test_words = [
        "плохоеслово",
        "оскорбление",
        "брань",
        "мат",
        "ругательство",
        # Добавьте реальные слова здесь
    ]
    
    print(f"Добавляю {len(test_words)} тестовых слов...")
    success = await ProfanityWordRepository.add_words(test_words)
    
    if success:
        all_words = await ProfanityWordRepository.get_all()
        print(f"✅ Слова добавлены. Всего в базе: {len(all_words)} слов")
        print(f"Список: {all_words}")
    else:
        print("❌ Ошибка при добавлении слов")
    
    await Database.close_pool()

if __name__ == "__main__":
    asyncio.run(add_test_words())
