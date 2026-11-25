from os import getenv

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID: int = int(getenv("ADMIN_CHAT_ID", "0"))
CHANNEL_LINK: str = getenv("CHANNEL_LINK", "https://t.me/your_channel")
MINI_APP_URL: str = getenv("MINI_APP_URL", "")
PORT: int = int(getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения (.env)")
if ADMIN_CHAT_ID == 0:
    raise ValueError("ADMIN_CHAT_ID не задан в переменных окружения (.env)")