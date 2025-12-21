import asyncio
import logging
from telegram import BotCommand
from telegram.ext import Application, CommandHandler
from config.settings import settings
from database.connection import Database
from database.migrations import run_migrations
from database.update_database import update_database_schema
from services.activity_service import ActivityService
from services.profanity_filter import ProfanityFilter
from handlers.user_handlers import UserHandlers
from handlers.admin_handlers import AdminHandlers
from handlers.error_handlers import error_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.LOG_LEVEL.upper())
)
logger = logging.getLogger(__name__)

async def set_bot_commands(application: Application):
    """Установка команд бота для быстрого доступа"""
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("changenick", "Изменить свою должность"),
        BotCommand("cn", "Изменить свою должность (краткая версия)"),
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

async def check_bot_info(application: Application):
    """Проверка информации о боте"""
    try:
        bot_info = await application.bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} (ID: {bot_info.id})")
        return bot_info
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return None

async def check_bot_admin_status(application: Application, chat_id: int):
    """Проверка статуса бота в чате"""
    try:
        chat_member = await application.bot.get_chat_member(chat_id, application.bot.id)
        logger.info(f"Bot status in chat {chat_id}: {chat_member.status}")
        logger.info(f"Bot is admin: {chat_member.status in ['administrator', 'creator']}")
        return chat_member
    except Exception as e:
        logger.error(f"Failed to get bot chat status: {e}")
        return None

async def main():
    """Основная функция запуска бота"""
    
    # Инициализация базы данных
    logger.info("Initializing database...")
    await Database.create_pool()
    
    # Обновляем схему базы данных
    await update_database_schema()
    
    # Выполняем миграции
    await run_migrations()
    
    # Создание фильтра матных слов
    profanity_filter = ProfanityFilter()
    await profanity_filter.load_words()
    
    # Создание сервиса активности
    activity_service = ActivityService()
    
    # Создание приложения бота
    application = Application.builder().token(settings.BOT_TOKEN).build()
    
    # Проверка информации о боте
    bot_info = await check_bot_info(application)
    
    # Проверка статуса бота в чате (если указан CHAT_ID)
    if hasattr(settings, 'CHAT_ID') and settings.CHAT_ID:
        await check_bot_admin_status(application, settings.CHAT_ID)
    else:
        logger.info("CHAT_ID not specified, skipping admin status check")
    
    # Сохраняем данные в bot_data
    application.bot_data['admin_ids'] = settings.ADMIN_IDS
    application.bot_data['activity_service'] = activity_service
    application.bot_data['profanity_filter'] = profanity_filter
    
    # Инициализация обработчиков
    user_handlers = UserHandlers(activity_service, profanity_filter)
    admin_handlers = AdminHandlers()
    
    # Добавление обработчиков
    for handler in user_handlers.get_handlers():
        application.add_handler(handler)
    
    for handler in admin_handlers.get_handlers():
        application.add_handler(handler)
    
    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)
    
    # Базовая команда /start
    async def start_command(update, context):
        help_text = (
            "🤖 *Бот для управления ролями в чате*\n\n"
            "📋 *Доступные команды:*\n"
            "• /changenick <ник> - изменить свою должность\n"
            "• /cn <ник> - краткая версия (то же самое)\n\n"
            "👨‍💼 *Для администраторов:*\n"
            "• /unblock <id> - разблокировать пользователя\n"
            "• /stats - статистика\n\n"
            "💡 *Совет:* Начните вводить / в чате, чтобы увидеть все команды!"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    application.add_handler(CommandHandler("start", start_command))
    
    # Запуск проверки активности
    await activity_service.start_activity_check(application)
    
    # Запуск бота
    logger.info("Starting bot...")
    await application.initialize()
    await application.start()
    
    # Установка команд для быстрого доступа
    await set_bot_commands(application)
    
    try:
        await application.updater.start_polling(
            allowed_updates=['message', 'chat_member', 'callback_query']
        )
        
        logger.info("✅ Bot is running and ready!")
        logger.info(f"👨‍💼 Admin IDs: {settings.ADMIN_IDS}")
        logger.info(f"🚫 Profanity words loaded: {len(profanity_filter.bad_words)}")
        logger.info(f"⏱️ Activity timeout: {settings.ACTIVITY_TIMEOUT_MINUTES} minutes")
        
        # Бесконечный цикл
        await asyncio.Event().wait()
        
    except asyncio.CancelledError:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        # Остановка
        await activity_service.stop()
        await application.stop()
        await Database.close_pool()

if __name__ == "__main__":
    asyncio.run(main())
