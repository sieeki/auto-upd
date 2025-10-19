import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="get server", callback_data="get_server")]
    ])
    await message.answer("Добро пожаловать!\nв данном боте ты можешь генерировать ссылки на приватный сервер!", reply_markup=keyboard)

@dp.callback_query(lambda call: call.data == "get_server")
async def button(call: types.CallbackQuery):
    await call.message.edit_text("тест")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())