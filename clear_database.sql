-- Очистка всех таблиц в правильном порядке (с учетом внешних ключей)
TRUNCATE TABLE role_history CASCADE;
TRUNCATE TABLE logs CASCADE;
TRUNCATE TABLE users CASCADE;

-- Сброс счетчиков auto-increment (для таблиц с serial primary key)
ALTER SEQUENCE logs_log_id_seq RESTART WITH 1;
ALTER SEQUENCE role_history_history_id_seq RESTART WITH 1;

-- Проверка, что таблицы пустые
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'logs' as table_name, COUNT(*) as row_count FROM logs
UNION ALL
SELECT 'role_history' as table_name, COUNT(*) as row_count FROM role_history;
