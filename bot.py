import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3

from config import BOT_TOKEN, CHANNEL_USERNAME, CHANNEL_URL, WELCOME_MESSAGE, SUCCESS_MESSAGE, NOT_SUBSCRIBED_MESSAGE
from database import Database

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Добавляем пользователя в базу
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Проверяем подписку сразу
    is_subscribed = await check_user_subscription(context.bot, user.id)
    
    if is_subscribed:
        # Пользователь уже подписан
        db.update_subscription(user.id, True)
        
        keyboard = [
            [InlineKeyboardButton("✅ Проверить подписку снова", callback_data="check_subscription")],
            [InlineKeyboardButton("📊 Информация", callback_data="info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🎉 Добро пожаловать!

✅ Вы уже подписаны на канал {CHANNEL_USERNAME}

Теперь вы можете пользоваться ботом!
Доступные команды:
/start - начать работу
/info - информация о вас
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        # Пользователь не подписан
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

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка подписки на канал"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    try:
        is_subscribed = await check_user_subscription(context.bot, user.id)
        
        if is_subscribed:
            # Пользователь подписан
            db.update_subscription(user.id, True)
            
            keyboard = [
                [InlineKeyboardButton("🏠 Главное меню", callback_data="menu")],
                [InlineKeyboardButton("📊 Информация", callback_data="info")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
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
        
        await query.edit_message_text(
            text=NOT_SUBSCRIBED_MESSAGE.format(CHANNEL_USERNAME),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /info"""
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    # Проверяем текущий статус подписки
    is_subscribed = await check_user_subscription(context.bot, user.id)
    
    if is_subscribed:
        status = "✅ Подписан"
        db.update_subscription(user.id, True)
    else:
        status = "❌ Не подписан"
        db.update_subscription(user.id, False)
    
    info_text = f"""
📊 Информация о вас:

👤 ID: {user.id}
📛 Имя: {user.first_name or 'Не указано'}
🔖 Username: @{user.username or 'Не указано'}
📢 Статус подписки: {status}

Канал: {CHANNEL_USERNAME}
    """
    
    if update.message:
        await update.message.reply_text(info_text)
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(info_text)

async def menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки меню"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Проверяем текущий статус подписки
    is_subscribed = await check_user_subscription(context.bot, user.id)
    
    if is_subscribed:
        # Пользователь подписан
        keyboard = [
            [InlineKeyboardButton("✅ Проверить подписку снова", callback_data="check_subscription")],
            [InlineKeyboardButton("📊 Информация", callback_data="info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🎉 Добро пожаловать!

✅ Вы уже подписаны на канал {CHANNEL_USERNAME}

Теперь вы можете пользоваться ботом!
        """
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        # Пользователь не подписан
        keyboard = [
            [InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL)],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            WELCOME_MESSAGE.format(CHANNEL_USERNAME),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

def main():
    """Основная функция запуска бота"""
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(menu_button, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(info_command, pattern="^info$"))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()