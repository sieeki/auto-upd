import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '8360956853:AAHAIotfoDmlwepaQZUroDWhMhjo_CgPwHE')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@dijitrail')
CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/dijitrail')
ADMIN_ID = int(os.getenv('ADMIN_ID', '7683939912'))

# Сообщения
WELCOME_MESSAGE = """
Привет! 👋

Для использования бота необходимо подписаться на наш канал: {}

После подписки нажмите кнопку ниже для проверки.
"""

SUCCESS_MESSAGE = """
✅ Отлично! Вы подписаны на канал.

Теперь вы можете пользоваться ботом!
Доступные команды:
/start - начать работу
/info - информация
"""

NOT_SUBSCRIBED_MESSAGE = """
❌ Вы не подписаны на канал {}

Пожалуйста, подпишитесь и нажмите кнопку проверки еще раз.
"""

# Добавьте в конец config.py
REFERRAL_MESSAGE = """
🎁 **Бесплатный браинрот**

💎 **Esok Sekolah Rainbow с мутациями**
💰 Приносит: **230 миллионов в секунду**
🎯 В наличии: **7 штук**

📊 **Ваша статистика:**
👥 Приглашено пользователей: **{invited_count}/30**
🎯 Осталось пригласить: **{needed_count}**

🔗 **Ваша реферальная ссылка:**
`{referral_link}`

📣 **Как получить награду:**
1. Пригласите 30 друзей по вашей ссылке
2. Каждый друг должен подписаться на канал
3. Получите Esok Sekolah Rainbow бесплатно!

⚡ **Успейте получить, всего 7 штук!**
"""