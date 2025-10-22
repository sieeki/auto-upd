import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web
import threading

TOKEN = os.getenv('BOT_TOKEN')
CHANNEL = "@dijitrail"
ADMIN_IDS = [7683939912]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# База данных SQLite
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot.db', check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, username TEXT, referrer_id INTEGER, 
                     referrals INTEGER DEFAULT 0, balance INTEGER DEFAULT 0, 
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS referral_links
                     (referrer_id INTEGER, referred_id INTEGER, 
                     UNIQUE(referrer_id, referred_id))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS admin_logs
                     (admin_id INTEGER, action TEXT, target_id INTEGER, 
                     amount INTEGER, reason TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()
    
    def add_user(self, user_id: int, username: str, referrer_id: int = None):
        c = self.conn.cursor()
        
        # Проверяем существует ли пользователь
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing_user = c.fetchone()
        
        if not existing_user:
            # Создаем пользователя
            c.execute("INSERT INTO users (user_id, username, referrer_id, balance) VALUES (?, ?, ?, ?)", 
                     (user_id, username, referrer_id, 0))
            
            # Обрабатываем реферала
            if referrer_id and referrer_id != user_id:
                c.execute("SELECT * FROM referral_links WHERE referrer_id = ? AND referred_id = ?", 
                         (referrer_id, user_id))
                if not c.fetchone():
                    # Добавляем в реферальные связи
                    c.execute("INSERT INTO referral_links (referrer_id, referred_id) VALUES (?, ?)", 
                             (referrer_id, user_id))
                    # Обновляем баланс и рефералы реферера
                    c.execute("UPDATE users SET referrals = referrals + 1, balance = balance + 1 WHERE user_id = ?", 
                             (referrer_id,))
        
        self.conn.commit()
    
    def get_user_data(self, user_id: int):
        c = self.conn.cursor()
        c.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        return result if result else (0, 0)
    
    def update_balance(self, user_id: int, amount: int):
        c = self.conn.cursor()
        
        # Проверяем существует ли пользователь
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not c.fetchone():
            # Создаем пользователя если не существует
            c.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)", 
                     (user_id, "unknown", max(0, amount)))
        else:
            # Обновляем баланс
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        
        self.conn.commit()
    
    def clear_balance(self, user_id: int):
        c = self.conn.cursor()
        c.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def get_all_users(self):
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = [row[0] for row in c.fetchall()]
        return users
    
    def add_admin_log(self, admin_id: int, action: str, target_id: int = None, amount: int = None, reason: str = None):
        c = self.conn.cursor()
        c.execute("INSERT INTO admin_logs (admin_id, action, target_id, amount, reason) VALUES (?, ?, ?, ?, ?)",
                 (admin_id, action, target_id, amount, reason))
        self.conn.commit()

# Создаем экземпляр базы данных
db = Database()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Команды для пользователей
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except:
            pass
    
    db.add_user(user_id, username, referrer_id)
    
    if await check_subscription(user_id):
        await show_main_menu(message, user_id)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL[1:]}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
        ])
        
        await message.answer("❌ <b>Сначала подпишись на наш канал!</b>", reply_markup=keyboard)

async def show_main_menu(message, user_id: int = None):
    if not user_id:
        user_id = message.from_user.id
    
    referrals_count, balance = db.get_user_data(user_id)
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥️ Получить сервер", callback_data="get_server")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="🛒 Покупка робуксов", callback_data="buy_robux")],
        [InlineKeyboardButton(text="📢 Наш канал", url=f"https://t.me/{CHANNEL[1:]}")]
    ])
    
    text = f"""<b>Добро пожаловать!</b>

✅ Ты подписан на канал!
👥 Приглашено друзей: <b>{referrals_count}</b>
💰 Баланс: <b>{balance} реф.</b>
🔗 Твоя реф ссылка: <code>{ref_link}</code>

1 друг = 1 реф. = 1 робукс!"""
    
    if isinstance(message, types.CallbackQuery):
        await message.message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)

# Админ команды
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="🗑️ Очистить баланс", callback_data="admin_clear_balance")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="◀️ Выйти из админки", callback_data="back_to_main")]
    ])
    
    await message.answer("🛠️ <b>Панель администратора</b>", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Доступ запрещен!")
        return
    
    users = db.get_all_users()
    total_balance = 0
    total_referrals = 0
    
    for user_id in users:
        referrals, balance = db.get_user_data(user_id)
        total_balance += balance
        total_referrals += referrals
    
    text = f"""<b>📊 Статистика бота</b>

👥 Всего пользователей: <b>{len(users)}</b>
💰 Общий баланс: <b>{total_balance}</b>
👥 Всего рефералов: <b>{total_referrals}</b>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="back_to_admin")]
    ])
    
    await call.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_menu(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Доступ запрещен!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="back_to_admin")]
    ])
    
    await call.message.edit_text(
        "💰 <b>Выдача баланса</b>\n\n"
        "Отправь сообщение в формате:\n"
        "<code>/add_balance user_id amount</code>\n\n"
        "Пример: <code>/add_balance 123456789 100</code>\n\n"
        "<i>Баланс будет добавлен к текущему</i>",
        reply_markup=keyboard
    )

@dp.message(Command("add_balance"))
async def add_balance_command(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❌ Неправильный формат!\nИспользуй: /add_balance user_id amount")
            return
        
        target_id = int(parts[1])
        amount = int(parts[2])
        
        # Получаем старый баланс
        old_referrals, old_balance = db.get_user_data(target_id)
        
        # Обновляем баланс
        db.update_balance(target_id, amount)
        db.add_admin_log(message.from_user.id, "add_balance", target_id, amount)
        
        # Получаем новый баланс
        _, new_balance = db.get_user_data(target_id)
        
        await message.answer(f"✅ Баланс пользователя {target_id} обновлен!\nБыло: {old_balance} реф.\nДобавлено: {amount} реф.\nСтало: {new_balance} реф.")
        
        # Уведомляем пользователя
        try:
            await bot.send_message(target_id, f"🎉 Администратор выдал тебе <b>{amount} реф.</b> на баланс!\n\nТвой баланс: {new_balance} реф.")
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Ошибка! user_id и amount должны быть числами")

@dp.message(Command("clear"))
async def clear_balance_command(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("❌ Неправильный формат!\nИспользуй: /clear user_id причина")
            return
        
        target_id = int(parts[1])
        reason = parts[2]
        
        old_referrals, old_balance = db.get_user_data(target_id)
        db.clear_balance(target_id)
        db.add_admin_log(message.from_user.id, "clear_balance", target_id, -old_balance, reason)
        
        await message.answer(f"✅ Баланс пользователя {target_id} очищен!\nБыло списано: {old_balance} реф.\nПричина: {reason}")
        
        # Уведомляем пользователя
        try:
            await bot.send_message(target_id, f"⚠️ <b>Ваш баланс очищен администратором!</b>\n\nПричина: {reason}\nСписано: {old_balance} реф.")
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Ошибка! user_id должен быть числом")

# Остальные обработчики
@dp.callback_query(F.data == "get_server")
async def get_server(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.answer()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        await call.message.edit_text("🖥️ <b>Твой приватный сервер:</b>\n<code>test-server.com</code>", reply_markup=keyboard)
    else:
        await call.answer("❌ Сначала подпишись на канал!", show_alert=True)

@dp.callback_query(F.data == "referrals")
async def show_referrals(call: types.CallbackQuery):
    referrals_count, balance = db.get_user_data(call.from_user.id)
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
    
    await call.answer()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    text = f"""<b>👥 Твоя реферальная статистика</b>

🔗 Твоя ссылка: <code>{ref_link}</code>
👥 Приглашено друзей: <b>{referrals_count}</b>
💰 Баланс: <b>{balance} реф.</b>

1 друг = 1 реф. = 1 робукс!"""
    
    await call.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "buy_robux")
async def buy_robux(call: types.CallbackQuery):
    referrals_count, balance = db.get_user_data(call.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Тестовый робукс (1 реф.)", callback_data="buy_test_robux")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    text = f"""<b>🛒 Магазин робуксов</b>

💰 Твой баланс: <b>{balance} реф.</b>
👥 Приглашено друзей: <b>{referrals_count}</b>

Выбери товар для покупки:"""
    
    await call.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "buy_test_robux")
async def buy_test_robux(call: types.CallbackQuery):
    referrals_count, balance = db.get_user_data(call.from_user.id)
    
    if balance >= 1:
        db.update_balance(call.from_user.id, -1)
        await call.answer("✅ Успешная покупка!", show_alert=True)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в магазин", callback_data="buy_robux")]
        ])
        await call.message.edit_text("🎉 <b>Ты купил тестовый робукс!</b>\n\nВот твой код: <code>TEST-ROBUX-123</code>", reply_markup=keyboard)
    else:
        await call.answer("❌ Недостаточно рефералов!", show_alert=True)

# Навигационные кнопки
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(call: types.CallbackQuery):
    await show_main_menu(call, call.from_user.id)

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Доступ запрещен!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="🗑️ Очистить баланс", callback_data="admin_clear_balance")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="◀️ Выйти из админки", callback_data="back_to_main")]
    ])
    
    await call.message.edit_text("🛠️ <b>Панель администратора</b>", reply_markup=keyboard)

@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await show_main_menu(call, call.from_user.id)
    else:
        await call.answer("❌ Ты еще не подписался на канал!", show_alert=True)

# Веб-сервер
async def handle(request):
    return web.Response(text="Bot is alive!")

def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    port = int(os.environ.get('PORT', 5000))
    web.run_app(app, host='0.0.0.0', port=port)

async def main():
    # Очищаем старые обновления перед запуском
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("🗑️ Старые обновления очищены!")
    except Exception as e:
        print(f"⚠️ Не удалось очистить обновления: {e}")
    
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    print("🤖 Бот запущен и работает!")
    print(f"👑 Админ ID: {ADMIN_IDS[0]}")
    print(f"📢 Канал: {CHANNEL}")
    
    # Запускаем polling с очисткой обновлений
    await dp.start_polling(bot, drop_pending_updates=True, allowed_updates=['message', 'callback_query'])

if __name__ == "__main__":
    asyncio.run(main())