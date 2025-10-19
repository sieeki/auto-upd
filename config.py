import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Другие настройки
ADMIN_IDS = [123456789]  # Замените на ваш ID
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Текстовые сообщения бота
MESSAGES = {
    'welcome': "Добро пожаловать!\nв данном боте ты можешь генерировать ссылки на приватный сервер!",
    'test': "тест",
    'error': "Произошла ошибка. Попробуйте позже."
}

# Настройки кнопок
BUTTONS = {
    'get_server': "get server"
}