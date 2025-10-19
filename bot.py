import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

# Токен бота
TOKEN = os.getenv('BOT_TOKEN')

def start(update, context):
    # Создаем кнопку
    button = InlineKeyboardButton("get server", callback_data="get_server")
    keyboard = InlineKeyboardMarkup([[button]])
    
    # Отправляем сообщение с кнопкой
    update.message.reply_text(
        "Добро пожаловать!\nв данном боте ты можешь генерировать ссылки на приватный сервер!", 
        reply_markup=keyboard
    )

def button_click(update, context):
    # Обрабатываем нажатие кнопки
    update.callback_query.answer()
    update.callback_query.edit_message_text(text="тест")

# Запускаем бота
updater = Updater(TOKEN)
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CallbackQueryHandler(button_click))

print("Бот запущен!")
updater.start_polling()
updater.idle()