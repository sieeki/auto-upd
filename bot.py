import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("get server", callback_data="get_server")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = "Добро пожаловать!\nв данном боте ты можешь генерировать ссылки на приватный сервер!"
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_server":
        await query.edit_message_text(text="тест")

def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()