import os

# Настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '8360956853:AAHAIotfoDmlwepaQZUroDWhMhjo_CgPwHE')

# Проверка токена
if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
    raise ValueError("Пожалуйста, установите BOT_TOKEN в переменных окружения!")

# Текстовые сообщения
MESSAGES = {
    'welcome': "Добро пожаловать!\nв данном боте ты можешь генерировать ссылки на приватный сервер!",
    'test': "тест"
}

# Настройки кнопок
BUTTONS = {
    'get_server': "get server"
}