import logging
from database.connection import Database

logger = logging.getLogger(__name__)

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    nickname VARCHAR(255),
    role_assigned BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    last_activity TIMESTAMP,
    warnings_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PROFANITY_WORDS_TABLE = """
CREATE TABLE IF NOT EXISTS profanity_words (
    id SERIAL PRIMARY KEY,
    word VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS logs (
    log_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ROLE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS role_history (
    history_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role_name VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP,
    reason VARCHAR(255)
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id);",
    "CREATE INDEX IF NOT EXISTS idx_users_role_assigned ON users(role_assigned);",
    "CREATE INDEX IF NOT EXISTS idx_users_is_blocked ON users(is_blocked);",
    "CREATE INDEX IF NOT EXISTS idx_profanity_words_word ON profanity_words(word);",
    "CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_role_history_user_id ON role_history(user_id);",
]

async def run_migrations():
    """Выполнение миграций"""
    try:
        # Создаем таблицы
        await Database.execute(CREATE_USERS_TABLE)
        await Database.execute(CREATE_PROFANITY_WORDS_TABLE)
        await Database.execute(CREATE_LOGS_TABLE)
        await Database.execute(CREATE_ROLE_HISTORY_TABLE)
        
        # Создаем индексы
        for index_query in CREATE_INDEXES:
            await Database.execute(index_query)
        
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        raise
