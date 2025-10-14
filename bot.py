import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3

from config import *
from database import Database

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
db = Database()

class SubscriptionBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("info", self.info_command))
        self.application.add_handler(CallbackQueryHandler(self.button_handler, pattern="^(check_subscription|menu)$"))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Добавляем пользователя в базу
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Создаем клавиатуру с кнопками
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL)],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            WELCOME_MESSAGE.format(CHANNEL_USERNAME),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def check_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка подписки на канал"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        try:
            # Получаем информацию о участнике канала
            chat_member = await context.bot.get_chat_member(
                chat_id=CHANNEL_USERNAME, 
                user_id=user.id
            )
            
            # Проверяем статус подписки
            if chat_member.status in ['member', 'administrator', 'creator']:
                # Пользователь подписан
                db.update_subscription(user.id, True)
                
                keyboard = [
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=SUCCESS_MESSAGE,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                # Пользователь не подписан
                raise Exception("Not subscribed")
                
        except Exception as e:
            # Ошибка или пользователь не подписан
            keyboard = [
                [InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL)],
                [InlineKeyboardButton("🔄 Проверить снова", callback_data="check_subscription")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=NOT_SUBSCRIBED_MESSAGE.format(CHANNEL_USERNAME),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /info"""
        user = update.effective_user
        user_data = db.get_user(user.id)
        
        if user_data and user_data[4]:  # subscribed status
            status = "✅ Подписан"
        else:
            status = "❌ Не подписан"
        
        info_text = f"""
📊 Информация о вас:

👤 ID: {user.id}
📛 Имя: {user.first_name or 'Не указано'}
🔖 Username: @{user.username or 'Не указано'}
📢 Статус подписки: {status}

Канал: {CHANNEL_USERNAME}
        """
        
        await update.message.reply_text(info_text)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "check_subscription":
            await self.check_subscription(update, context)
        elif query.data == "menu":
            await self.start_command(update, context)
    
    def run(self):
        """Запуск бота"""
        print("Бот запущен...")
        self.application.run_polling()

# Запуск бота
if __name__ == "__main__":
    bot = SubscriptionBot(BOT_TOKEN)
    bot.run()
