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
def get_connection():
    return sqlite3.connect('bot.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
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
    conn.commit()
    conn.close()

init_db()

def add_user(user_id: int, username: str, referrer_id: int = None):
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = c.fetchone()
    
    if not existing_user:
        c.execute("INSERT INTO users (user_id, username, referrer_id, balance) VALUES (?, ?, ?, ?)", 
                 (user_id, username, referrer_id, 0))
        
        # Защита от повторных рефералов
        if referrer_id and referrer_id != user_id:
            c.execute("SELECT * FROM referral_links WHERE referrer_id = ? AND referred_id = ?", 
                     (referrer_id, user_id))
            if not c.fetchone():
                c.execute("INSERT INTO referral_links (referrer_id, referred_id) VALUES (?, ?)", 
                         (referrer_id, user_id))
                c.execute("UPDATE users SET referrals = referrals + 1, balance = balance + 1 WHERE user_id = ?", 
                         (referrer_id,))
    
    conn.commit()
    conn.close()

def get_user_data(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (0, 0)

def update_balance(user_id: int, amount: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def clear_balance(user_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def add_admin_log(admin_id: int, action: str, target_id: int = None, amount: int = None, reason: str = None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO admin_logs (admin_id, action, target_id, amount, reason) VALUES (?, ?, ?, ?, ?)",
             (admin_id, action, target_id, amount, reason))
    conn.commit()
    conn.close()

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
    
    add_user(user_id, username, referrer_id)
    
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
    
    referrals_count, balance = get_user_data(user_id)
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
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(balance) FROM users")
    total_balance = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(referrals) FROM users")
    total_referrals = c.fetchone()[0] or 0
    conn.close()
    
    text = f"""<b>📊 Статистика бота</b>

👥 Всего пользователей: <b>{total_users}</b>
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

@dp.callback_query(F.data == "admin_clear_balance")
async def admin_clear_balance_menu(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Доступ запрещен!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="back_to_admin")]
    ])
    
    await call.message.edit_text(
        "🗑️ <b>Очистка баланса</b>\n\n"
        "Отправь сообщение в формате:\n"
        "<code>/clear user_id причина</code>\n\n"
        "Пример: <code>/clear 123456789 Нарушение правил</code>\n\n"
        "<i>Причина будет отправлена пользователю</i>",
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
        
        update_balance(target_id, amount)
        add_admin_log(message.from_user.id, "add_balance", target_id, amount)
        
        await message.answer(f"✅ Баланс пользователя {target_id} увеличен на {amount} реф.")
        
        # Уведомляем пользователя
        try:
            await bot.send_message(target_id, f"🎉 Администратор выдал тебе <b>{amount} реф.</b> на баланс!")
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
        
        old_balance = get_user_data(target_id)[1]
        clear_balance(target_id)
        add_admin_log(message.from_user.id, "clear_balance", target_id, -old_balance, reason)
        
        await message.answer(f"✅ Баланс пользователя {target_id} очищен (было: {old_balance} реф.)\nПричина: {reason}")
        
        # Уведомляем пользователя
        try:
            await bot.send_message(target_id, f"⚠️ <b>Ваш баланс очищен администратором!</b>\n\nПричина: {reason}\nБыло списано: {old_balance} реф.")
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Ошибка! user_id должен быть числом")

@dp.message(Command("broadcast"))
async def broadcast_command(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    broadcast_text = message.text.replace('/broadcast', '').strip()
    
    if not broadcast_text:
        await message.answer("❌ Введите текст для рассылки!")
        return
    
    # Парсим кнопку если есть
    button_text = None
    button_url = None
    if ' | ' in broadcast_text:
        parts = broadcast_text.split(' | ')
        if len(parts) >= 3:
            broadcast_text = parts[0]
            button_text = parts[1]
            button_url = parts[2]
    
    users = get_all_users()
    success = 0
    failed = 0
    
    await message.answer(f"🔄 Начинаю рассылку для {len(users)} пользователей...")
    
    for user_id in users:
        try:
            if button_text and button_url:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=button_text, url=button_url)]
                ])
                await bot.send_message(user_id, broadcast_text, reply_markup=keyboard)
            else:
                await bot.send_message(user_id, broadcast_text)
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)
    
    add_admin_log(message.from_user.id, "broadcast", None, len(users))
    await message.answer(f"✅ Рассылка завершена!\nУспешно: {success}\nНе удалось: {failed}")

@dp.message(Command("broadcast_photo"))
async def broadcast_photo_command(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    if not message.photo:
        await message.answer("❌ Прикрепи фото к сообщению!")
        return
    
    caption = message.caption.replace('/broadcast_photo', '').strip() if message.caption else ""
    
    # Парсим кнопку если есть
    button_text = None
    button_url = None
    if ' | '