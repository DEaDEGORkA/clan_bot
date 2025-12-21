import logging
from database.connection import Database

logger = logging.getLogger(__name__)

async def update_database_schema():
    """Обновление схемы базы данных - удаление колонки correct_answer"""
    try:
        # Проверяем, существует ли колонка correct_answer
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='correct_answer'
        """
        result = await Database.fetchval(check_query)
        
        if result:
            logger.info("Removing 'correct_answer' column from users table...")
            # Удаляем колонку
            alter_query = "ALTER TABLE users DROP COLUMN correct_answer"
            await Database.execute(alter_query)
            logger.info("Column 'correct_answer' removed successfully")
        else:
            logger.info("Column 'correct_answer' does not exist, skipping")
        
        return True
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False
