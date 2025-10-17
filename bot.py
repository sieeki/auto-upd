import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3

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
        ]
        
        # Добавляем админские кнопки если пользователь админ
        if is_admin(user.id):
            keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🎉 Добро пожаловать!

✅ Вы уже подписаны на канал {CHANNEL_USERNAME}

Теперь вы можете пользоваться ботом!
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
            ]
            
            # Добавляем админские кнопки если пользователь админ
            if is_admin(user.id):
                keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
                
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
        ]
        
        # Добавляем админские кнопки если пользователь админ
        if is_admin(user.id):
            keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
            
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

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ панель"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if not is_admin(user.id):
        await query.edit_message_text("❌ У вас нет доступа к админ панели")
        return
    
    # Получаем статистику
    total_users = db.get_user_count()
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
    subscribed_users = cursor.fetchone()[0]
    conn.close()
    
    admin_text = f"""
👑 Админ панель

📊 Статистика:
👥 Всего пользователей: {total_users}
✅ Подписаны на канал: {subscribed_users}
❌ Не подписаны: {total_users - subscribed_users}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_panel")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(admin_text, reply_markup=reply_markup)

def setup_handlers(application):
    """Настройка обработчиков для бота"""
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    
    # Обработчики callback кнопок
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(menu_button, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))

def main():
    """Основная функция запуска бота"""
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()