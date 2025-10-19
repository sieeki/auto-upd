import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import BOT_TOKEN, MESSAGES, BUTTONS

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    try:
        keyboard = [
            [InlineKeyboardButton(BUTTONS['get_server'], callback_data="get_server")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            MESSAGES['welcome'], 
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        logger.info(f"User {update.effective_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start_command: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на кнопки"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "get_server":
            await query.edit_message_text(text=MESSAGES['test'])
            logger.info(f"User {query.from_user.id} pressed 'get_server'")
            
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main() -> None:
    """Основная функция запуска бота"""
    try:
        # Проверяем токен
        if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            logger.error("BOT_TOKEN не установлен!")
            sys.exit(1)
            
        logger.info("Создаем приложение бота...")
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("Бот запускается...")
        print("🤖 Бот успешно запущен и ожидает сообщений...")
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()