import os
import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

TOKEN = os.getenv('BOT_TOKEN')

def start(update, context):
    keyboard = [[telegram.InlineKeyboardButton("get server", callback_data="get_server")]]
    reply_markup = telegram.InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Добро пожаловать!\nв данном боте ты можешь генерировать ссылки на приватный сервер!", reply_markup=reply_markup)

def button(update, context):
    update.callback_query.answer()
    update.callback_query.edit_message_text(text="тест")

updater = Updater(TOKEN)
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CallbackQueryHandler(button))
updater.start_polling()
updater.idle()