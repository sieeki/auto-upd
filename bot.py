import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask, request
import threading

from config import BOT_TOKEN, CHANNEL_USERNAME, CHANNEL_URL, WELCOME_MESSAGE, SUCCESS_MESSAGE, NOT_SUBSCRIBED_MESSAGE, ADMIN_ID
from database import Database

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

# Состояния для рассылки
BROADCAST_STATE = {}

# Flask app для webhook
app = Flask(__name__)

def is_admin(user_id):
    """Проверяет является ли пользователь админом"""
    return user_id == ADMIN_ID

async def check_user_subscription(bot, user_id):
    """Проверяет подписку пользователя на канал"""
    try:
        chat_member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, 
            user_id=user_id
        )
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

# ... ВСЕ ФУНКЦИИ БОТА ОСТАЮТСЯ ПРЕЖНИМИ ...
# (start_command, check_subscription, info_command, menu_button, admin_panel, stats_command, 
#  broadcast_command, cancel_broadcast, handle_broadcast_message, admin_stats_button, admin_broadcast_button)

def setup_handlers(application):
    """Настройка обработчиков для бота"""
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("cancel", cancel_broadcast))
    
    # Обработчики callback кнопок
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(menu_button, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(info_command, pattern="^info$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_stats_button, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_button, pattern="^broadcast$"))
    
    # Обработчик сообщений для рассылки
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message))

def run_polling():
    """Запуск бота в режиме polling (для локальной разработки)"""
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    print("🔄 Бот запущен в режиме polling...")
    application.run_polling()

@app.route('/')
def home():
    return "🤖 Бот работает!"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook от Telegram"""
    if request.method == "POST":
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put(update)
    return "OK"

@app.route('/set_webhook')
def set_webhook():
    """Установка webhook"""
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')}/webhook"
    try:
        application.bot.set_webhook(webhook_url)
        return f"✅ Webhook установлен: {webhook_url}"
    except Exception as e:
        return f"❌ Ошибка: {e}"

def run_webhook():
    """Запуск бота в режиме webhook (для production)"""
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=application.run_webhook, daemon=True)
    thread.start()
    print("🌐 Бот запущен в режиме webhook...")
    
    # Запускаем Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def main():
    """Основная функция запуска бота"""
    # Проверяем, запущено ли на Render (есть ли PORT)
    if os.environ.get('RENDER'):
        print("🚀 Запуск в режиме webhook (Render)")
        run_webhook()
    else:
        print("💻 Запуск в режиме polling (локально)")
        run_polling()

if __name__ == "__main__":
    main()