import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

# Чтение токена из переменной окружения
TOKEN_bot = os.getenv("BOT_TOKEN")
api_key = os.getenv("api_key")

if not TOKEN_bot:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")
if not api_key:
    raise ValueError("Нет ключа api для погоды!")