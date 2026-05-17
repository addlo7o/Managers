import os
from dotenv import load_dotenv

load_dotenv()

# ===== توکن و اطلاعات اصلی =====
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "6387049405"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")

# ===== کانال‌های اجباری (تا ۵ کانال) =====
FORCE_SUB_CHANNELS = []
for i in range(1, 6):
    ch = os.getenv(f"FORCE_CHANNEL_{i}")
    if ch:
        FORCE_SUB_CHANNELS.append(ch)

FORCE_SUB_IDS = []
for i in range(1, 6):
    ch_id = os.getenv(f"FORCE_CHANNEL_ID_{i}")
    if ch_id:
        FORCE_SUB_IDS.append(int(ch_id))

# ===== دسترسی‌ها =====
SUDO_USERS = list(map(int, os.getenv("SUDO_USERS", "6387049405").split(",")))
DEV_USERS = list(map(int, os.getenv("DEV_USERS", "6387049405").split(",")))

# ===== لاگ و بکاپ =====
LOGGER_GROUP = int(os.getenv("LOGGER_GROUP", "0"))
BACKUP_CHAT = int(os.getenv("BACKUP_CHAT", "0"))
WELCOME_PIC = os.getenv("WELCOME_PIC", "")

# ===== متن‌های پیش‌فرض =====
WELCOME_DEFAULT = (
    "✨ **خوش آمدید {mention} عزیز!**\n\n"
    "📌 حتماً توی کانال عضو شو!\n"
    "📢 @{channel}"
)
GOODBYE_DEFAULT = "😢 **{mention} رفت...**\n\nامیدوارم برگردی!"

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN رو توی Environment Variables ست کن!")
