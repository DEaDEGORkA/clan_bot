import asyncpg
import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class Database:
    _pool: Optional[asyncpg.Pool] = None
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            await cls.create_pool()
        return cls._pool
    
    @classmethod
    async def create_pool(cls):
        """Создание пула подключений"""
        try:
            cls._pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                ssl=settings.DB_SSL_MODE if settings.DB_SSL_MODE != 'disable' else None,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    @classmethod
    async def close_pool(cls):
        """Закрытие пула подключений"""
        if cls._pool:
            await cls._pool.close()
            logger.info("Database connection pool closed")
    
    @classmethod
    async def execute(cls, query: str, *args):
        """Выполнение запроса"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    @classmethod
    async def fetch(cls, query: str, *args):
        """Получение нескольких записей"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    @classmethod
    async def fetchrow(cls, query: str, *args):
        """Получение одной записи"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    @classmethod
    async def fetchval(cls, query: str, *args):
        """Получение одного значения"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)