import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

TOKEN = os.getenv('BOT_TOKEN')
CHANNEL = "@dijitrail"  # Замени на username своего канала

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# База данных
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, referrer_id INTEGER, referrals INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

def add_user(user_id: int, username: str, referrer_id: int = None):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", 
                 (user_id, username, referrer_id))
        
        if referrer_id:
            c.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
    
    conn.commit()
    conn.close()

def get_referrals_count(user_id: int) -> int:
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

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
    
    # Обработка реферальной ссылки
    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except:
            pass
    
    add_user(user_id, username, referrer_id)
    
    # Проверяем подписку
    if await check_subscription(user_id):
        referrals_count = get_referrals_count(user_id)
        ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖥️ Получить сервер", callback_data="get_server")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
            [InlineKeyboardButton(text="📢 Наш канал", url=f"https://t.me/{CHANNEL[1:]}")]
        ])
        
        text = f"""<b>Добро пожаловать!</b>

✅ Ты подписан на канал!
👥 Приглашено друзей: <b>{referrals_count}</b>
🔗 Твоя реф ссылка: <code>{ref_link}</code>

Нажми кнопку ниже чтобы получить сервер:"""
        
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
    referrals_count = get_referrals_count(call.from_user.id)
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
    
    await call.answer()
    
    text = f"""<b>👥 Твоя реферальная статистика</b>

🔗 Твоя ссылка: <code>{ref_link}</code>
👥 Приглашено друзей: <b>{referrals_count}</b>

Приглашай друзей и получай бонусы!"""
    
    await call.message.edit_text(text)

@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        referrals_count = get_referrals_count(call.from_user.id)
        ref_link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖥️ Получить сервер", callback_data="get_server")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")]
        ])
        
        text = f"""<b>Отлично! ✅</b>

Теперь ты подписан на канал!
👥 Приглашено друзей: <b>{referrals_count}</b>
🔗 Твоя реф ссылка: <code>{ref_link}</code>

Нажми кнопку ниже чтобы получить сервер:"""
        
        await call.message.edit_text(text, reply_markup=keyboard)
    else:
        await call.answer("❌ Ты еще не подписался на канал!", show_alert=True)

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())