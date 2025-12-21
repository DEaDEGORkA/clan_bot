#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import Database
from database.repositories import UserRepository

async def check_user_permissions():
    """Проверка пользователей и их прав"""
    await Database.create_pool()
    
    # Получаем всех пользователей
    users = await UserRepository.get_by_chat_and_role(settings.CHAT_ID, None)
    
    print("=== Пользователи в базе данных ===")
    print(f"Всего пользователей: {len(users)}")
    print()
    
    for user in users:
        status = "✅" if user.role_assigned else "❌"
        nickname = user.nickname or "Нет ника"
        print(f"{status} ID: {user.user_id}, Ник: {nickname}, Роль: {user.role_assigned}, "
              f"Блокировка: {user.is_blocked}, Предупреждения: {user.warnings_count}")
    
    await Database.close_pool()

if __name__ == "__main__":
    from config.settings import settings
    asyncio.run(check_user_permissions())
