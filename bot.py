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

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# База данных
def init_db():
    conn = sqlite3.connect('bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, referrer_id INTEGER, referrals INTEGER DEFAULT 0, balance INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

def add_user(user_id: int, username: str, referrer_id: int = None):
    conn = sqlite3.connect('bot.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, referrer_id, balance) VALUES (?, ?, ?, ?)", 
                 (user_id, username, referrer_id, 0))
        
        if referrer_id:
            c.execute("UPDATE users SET referrals = referrals + 1, balance = balance + 1 WHERE user_id = ?", (referrer_id,))
    
    conn.commit()
    conn.close()

def get_user_data(user_id: int):
    conn = sqlite3.connect('bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (0, 0)

def update_balance(user_id: int, amount: int):
    conn = sqlite3.connect('bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

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
        
        await message.answer(text, reply_markup=keyboard)
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL[1:]}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
        ])
        
        await message.answer("❌ <b>Сначала подпишись на наш канал!</b>", reply_markup=keyboard)

@dp.callback_query(F.data == "get_server")
async def get_server(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.answer()
        await call.message.edit_text("🖥️ <b>Твой приватный сервер:</b>\n<code>test-server.com</code>")
    else:
        await call.answer("❌ Сначала подпишись на канал!", show_alert=True)

@dp.callback_query(F.data == "referrals")
async def show_referrals(call: types.CallbackQuery):
    referrals_count, balance = get_user_data(call.from_user.id)
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
    
    await call.answer()
    
    text = f"""<b>👥 Твоя реферальная статистика</b>

🔗 Твоя ссылка: <code>{ref_link}</code>
👥 Приглашено друзей: <b>{referrals_count}</b>
💰 Баланс: <b>{balance} реф.</b>

1 друг = 1 реф. = 1 робукс!"""
    
    await call.message.edit_text(text)

@dp.callback_query(F.data == "buy_robux")
async def buy_robux(call: types.CallbackQuery):
    referrals_count, balance = get_user_data(call.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Тестовый робукс (1 реф.)", callback_data="buy_test_robux")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    text = f"""<b>🛒 Магазин робуксов</b>

💰 Твой баланс: <b>{balance} реф.</b>
👥 Приглашено друзей: <b>{referrals_count}</b>

Выбери товар для покупки:"""
    
    await call.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "buy_test_robux")
async def buy_test_robux(call: types.CallbackQuery):
    referrals_count, balance = get_user_data(call.from_user.id)
    
    if balance >= 1:
        update_balance(call.from_user.id, -1)
        await call.answer("✅ Успешная покупка!", show_alert=True)
        await call.message.edit_text("🎉 <b>Ты купил тестовый робукс!</b>\n\nВот твой код: <code>TEST-ROBUX-123</code>")
    else:
        await call.answer("❌ Недостаточно рефералов!", show_alert=True)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(call: types.CallbackQuery):
    referrals_count, balance = get_user_data(call.from_user.id)
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥️ Получить сервер", callback_data="get_server")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="🛒 Покупка робуксов", callback_data="buy_robux")],
        [InlineKeyboardButton(text="📢 Наш канал", url=f"https://t.me/{CHANNEL[1:]}")]
    ])
    
    text = f"""<b>Главное меню</b>

✅ Ты подписан на канал!
👥 Приглашено друзей: <b>{referrals_count}</b>
💰 Баланс: <b>{balance} реф.</b>
🔗 Твоя реф ссылка: <code>{ref_link}</code>

1 друг = 1 реф. = 1 робукс!"""
    
    await call.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        referrals_count, balance = get_user_data(call.from_user.id)
        ref_link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖥️ Получить сервер", callback_data="get_server")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
            [InlineKeyboardButton(text="🛒 Покупка робуксов", callback_data="buy_robux")]
        ])
        
        text = f"""<b>Отлично! ✅</b>

Теперь ты подписан на канал!
👥 Приглашено друзей: <b>{referrals_count}</b>
💰 Баланс: <b>{balance} реф.</b>
🔗 Твоя реф ссылка: <code>{ref_link}</code>

1 друг = 1 реф. = 1 робукс!"""
        
        await call.message.edit_text(text, reply_markup=keyboard)
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
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    print("🤖 Бот запущен и работает!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())