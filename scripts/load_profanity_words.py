#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import Database
from database.repositories import ProfanityWordRepository

async def load_profanity_words_from_file(filename: str):
    """Загрузка матных слов из файла в базу данных"""
    try:
        # Подключаемся к базе данных
        await Database.create_pool()
        
        # Читаем слова из файла
        with open(filename, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]
        
        print(f"Найдено {len(words)} слов в файле {filename}")
        
        # Очищаем старые слова (опционально)
        clear = input("Очистить старые слова перед загрузкой? (y/N): ").strip().lower()
        if clear == 'y':
            await ProfanityWordRepository.clear_all()
            print("Старые слова очищены")
        
        # Добавляем слова в базу
        success = await ProfanityWordRepository.add_words(words)
        
        if success:
            print(f"✅ Успешно добавлено {len(words)} слов в базу данных")
            
            # Проверяем сколько теперь слов в базе
            all_words = await ProfanityWordRepository.get_all()
            print(f"📊 Всего слов в базе: {len(all_words)}")
        else:
            print("❌ Ошибка при добавлении слов")
            
    except FileNotFoundError:
        print(f"❌ Файл не найден: {filename}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await Database.close_pool()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python load_profanity_words.py <файл_со_словами.txt>")
        print("Формат файла: каждое слово на новой строке")
        sys.exit(1)
    
    asyncio.run(load_profanity_words_from_file(sys.argv[1]))
