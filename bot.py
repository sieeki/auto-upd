import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask, request
import threading
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
        
        # Добавляем админские кнопки если пользователь админ
        if is_admin(user.id):
            keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
            
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

⚙️ Доступные команды:
/broadcast - рассылка сообщения
/stats - подробная статистика
/debug - отладочная информация
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🐛 Отладка", callback_data="debug")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(admin_text, reply_markup=reply_markup)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда статистики /stats"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return
    
    # Получаем статистику
    total_users = db.get_user_count()
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
    subscribed_users = cursor.fetchone()[0]
    
    # Последние 5 пользователей
    cursor.execute('SELECT user_id, username, first_name, subscribed, created_at FROM users ORDER BY created_at DESC LIMIT 5')
    recent_users = cursor.fetchall()
    conn.close()
    
    stats_text = f"""
📊 Детальная статистика

👥 Всего пользователей: {total_users}
✅ Подписаны на канал: {subscribed_users}
❌ Не подписаны: {total_users - subscribed_users}

📈 Охват: {round((subscribed_users / total_users * 100) if total_users > 0 else 0, 1)}%

🆕 Последние пользователи:
"""
    
    for user_data in recent_users:
        user_id, username, first_name, subscribed, created_at = user_data
        status = "✅" if subscribed else "❌"
        username_display = f"@{username}" if username else "без username"
        stats_text += f"{status} {first_name} ({username_display})\n"
    
    await update.message.reply_text(stats_text)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда рассылки /broadcast"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return
    
    BROADCAST_STATE[user.id] = True
    await update.message.reply_text(
        "📢 Режим рассылки активирован. Отправьте сообщение для рассылки всем пользователям.\n\n"
        "❌ Для отмены отправьте /cancel"
    )

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена рассылки"""
    user = update.effective_user
    
    if user.id in BROADCAST_STATE:
        del BROADCAST_STATE[user.id]
        await update.message.reply_text("❌ Рассылка отменена")
    else:
        await update.message.reply_text("❌ Нет активной рассылки для отмены")

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщения для рассылки"""
    user = update.effective_user
    
    if user.id not in BROADCAST_STATE:
        return
    
    if not is_admin(user.id):
        return
    
    message = update.message
    broadcast_text = message.text or message.caption
    
    if not broadcast_text:
        await update.message.reply_text("❌ Сообщение не содержит текста")
        return
    
    # Получаем всех пользователей из базы
    all_users = db.get_all_users()
    total_users = len(all_users)
    
    if total_users == 0:
        await update.message.reply_text("❌ В базе нет пользователей для рассылки")
        del BROADCAST_STATE[user.id]
        return
    
    successful_sends = 0
    failed_sends = 0
    failed_users = []
    
    # Отправляем сообщение о начале рассылки
    progress_msg = await update.message.reply_text(f"🔄 Начинаем рассылку для {total_users} пользователей...")
    
    # Рассылаем сообщение ВСЕМ пользователям из базы
    for user_tuple in all_users:
        user_id = user_tuple[0]
        
        # Пропускаем рассылку самому себе (админу)
        if user_id == user.id:
            successful_sends += 1
            continue
            
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Рассылка:\n\n{broadcast_text}"
            )
            successful_sends += 1
            
        except Exception as e:
            failed_sends += 1
            failed_users.append(user_id)
            logger.error(f"Failed to send to {user_id}: {e}")
    
    # Завершаем рассылку
    del BROADCAST_STATE[user.id]
    
    # Формируем результат
    result_text = f"""
✅ Рассылка завершена!

📊 Результаты:
👥 Всего пользователей в базе: {total_users}
✅ Успешно отправлено: {successful_sends}
❌ Не удалось отправить: {failed_sends}
📈 Успех: {round((successful_sends / total_users * 100) if total_users > 0 else 0, 1)}%
"""
    
    # Добавляем информацию о неудачных отправках
    if failed_sends > 0:
        result_text += f"\n❌ Не удалось отправить {failed_sends} пользователям"
    
    await progress_msg.edit_text(result_text)

async def debug_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для отладки - показывает всех пользователей в базе"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде")
        return
    
    # Получаем всех пользователей из базы
    all_users = db.get_all_users()
    user_count = db.get_user_count()
    
    debug_text = f"""
🔧 Отладочная информация:

👥 Всего пользователей в базе: {user_count}
📋 Список пользователей:
"""
    
    # Получаем подробную информацию о каждом пользователе
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, subscribed FROM users')
    detailed_users = cursor.fetchall()
    conn.close()
    
    for user_data in detailed_users:
        user_id, username, first_name, subscribed = user_data
        status = "✅" if subscribed else "❌"
        username_display = f"@{username}" if username else "без username"
        name_display = first_name or "без имени"
        
        debug_text += f"{status} {name_display} ({username_display}) - ID: {user_id}\n"
    
    await update.message.reply_text(debug_text)

async def admin_stats_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки статистики в админ панели"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if not is_admin(user.id):
        await query.edit_message_text("❌ У вас нет доступа")
        return
    
    # Получаем статистику
    total_users = db.get_user_count()
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
    subscribed_users = cursor.fetchone()[0]
    conn.close()
    
    stats_text = f"""
📊 Статистика:

👥 Всего пользователей: {total_users}
✅ Подписаны на канал: {subscribed_users}
❌ Не подписаны: {total_users - subscribed_users}

📈 Охват: {round((subscribed_users / total_users * 100) if total_users > 0 else 0, 1)}%
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="stats")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def admin_broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки рассылки в админ панели"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if not is_admin(user.id):
        await query.edit_message_text("❌ У вас нет доступа")
        return
    
    BROADCAST_STATE[user.id] = True
    
    keyboard = [
        [InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 Режим рассылки активирован. Отправьте сообщение для рассылки всем пользователям.\n\n"
        "❌ Для отмены нажмите кнопку ниже",
        reply_markup=reply_markup
    )

async def admin_debug_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки отладки в админ панели"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if not is_admin(user.id):
        await query.edit_message_text("❌ У вас нет доступа")
        return
    
    await debug_users(update, context)

def setup_handlers(application):
    """Настройка обработчиков для бота"""
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("cancel", cancel_broadcast))
    application.add_handler(CommandHandler("debug", debug_users))
    
    # Обработчики callback кнопок
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(menu_button, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(info_command, pattern="^info$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_stats_button, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_button, pattern="^broadcast$"))
    application.add_handler(CallbackQueryHandler(admin_debug_button, pattern="^debug$"))
    
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
    return "OK"

@app.route('/set_webhook')
def set_webhook():
    """Установка webhook"""
    return "Webhook setup would be here"

def run_webhook():
    """Запуск бота в режиме webhook (для production)"""
    # Для простоты на Render используем polling
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    print("🚀 Бот запущен в режиме polling на Render...")
    application.run_polling()

def main():
    """Основная функция запуска бота"""
    # Всегда используем polling для простоты
    print("🚀 Запуск бота...")
    run_webhook()

if __name__ == "__main__":
    main()