#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v5.0 — Persian Premium Edition
# ============================================

import asyncio
import logging
import re
import os
from datetime import datetime, timedelta

from database import init_db, get_db, get_setting, set_setting

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, BotCommand, MessageEntity
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ===== تنظیم لاگ =====
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== توکن ربات از متغیر محیطی =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ متغیر محیطی BOT_TOKEN تنظیم نشده است!")

# ===== تنظیمات پیشفرض =====
SUDO_USERS = list(map(int, os.getenv("SUDO_USERS", "").split(","))) if os.getenv("SUDO_USERS") else []
FORCE_SUB_CHANNELS = os.getenv("FORCE_SUB_CHANNELS", "https://t.me/dontworry80").split(",")
FORCE_SUB_IDS = list(map(int, os.getenv("FORCE_SUB_IDS", "0").split(","))) if os.getenv("FORCE_SUB_IDS") else [0]
GOODBYE_DEFAULT = "😢 {mention} از گروه خارج شد!"

FORCE_SUB_CHANNEL = FORCE_SUB_CHANNELS[0] if FORCE_SUB_CHANNELS else "https://t.me/dontworry80"
FORCE_SUB_USERNAME = "@dontworry80"

# ===== لیست سیاه =====
SPAM_KEYWORDS = ["join", "fast", "سایت", "🔞", "💰", "کلیک", "عضویت"]
FORBIDDEN_DOMAINS = ["bit.ly", "tinyurl.com", "t.me/+"]

BAD_WORDS = [
    "احمق", "خر", "گاو", "کودن", "نادان", "بی‌شعور", "بیشعور",
    "ابله", "حیوان", "مادرجنده", "کصکش", "کیر", "کون", "جنده",
    "اوبی", "عوضی", "بی‌ناموس", "بیناموس", "الاغ", "خفه",
]

warnings = {}

# ============================================
# ✨ ایموجی‌های پریمیوم
# ============================================

CUSTOM_EMOJIS = {
    "heart_blue": {"id": "5377688663960331522", "char": "💙", "length": 2},
    "heart_blue2": {"id": "5377855630813964361", "char": "💙", "length": 2},
    "laugh": {"id": "6269133349860677188", "char": "😂", "length": 2},
    "cry": {"id": "6269219987940972511", "char": "😭", "length": 2},
    "heart_red": {"id": "5370897968478047651", "char": "❤️", "length": 2},
    "heart_red2": {"id": "5370792982297463610", "char": "❤️", "length": 2},
    "alert": {"id": "5379995211722138153", "char": "🚨", "length": 2},
    "earth": {"id": "5377357058125340868", "char": "🌎", "length": 2},
    "grin": {"id": "5233605022419270727", "char": "😁", "length": 2},
    "cool": {"id": "5114163768623895481", "char": "🆒", "length": 2},
    "check": {"id": "5208880351690112495", "char": "✅", "length": 1},
}

def build_emoji_entity(emoji_id: str, offset: int = 0, length: int = 2) -> MessageEntity:
    return MessageEntity(
        type=MessageEntity.CUSTOM_EMOJI,
        offset=offset,
        length=length,
        custom_emoji_id=emoji_id,
    )

def get_premium_prefix() -> tuple:
    emoji_list = [
        CUSTOM_EMOJIS["grin"],
        CUSTOM_EMOJIS["heart_red"],
        CUSTOM_EMOJIS["heart_blue"],
        CUSTOM_EMOJIS["earth"],
        CUSTOM_EMOJIS["cool"],
    ]
    
    text = ""
    entities = []
    offset = 0
    
    for emoji in emoji_list:
        text += emoji["char"]
        entities.append(build_emoji_entity(emoji["id"], offset, emoji["length"]))
        offset += emoji["length"]
    
    return text + "\n", entities

async def send_premium(chat_id, text: str, context: ContextTypes.DEFAULT_TYPE,
                        reply_to_message_id=None, parse_mode=ParseMode.MARKDOWN):
    prefix, prefix_entities = get_premium_prefix()
    full_text = prefix + text
    
    try:
        return await context.bot.send_message(
            chat_id=chat_id,
            text=full_text,
            entities=prefix_entities,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as e:
        logger.error(f"خطا: {e}")
        return await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )

async def reply_premium(update: Update, text: str, context: ContextTypes.DEFAULT_TYPE,
                         reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    prefix, prefix_entities = get_premium_prefix()
    full_text = prefix + text
    
    try:
        return await update.message.reply_text(
            full_text,
            entities=prefix_entities,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except Exception as e:
        logger.error(f"خطا: {e}")
        return await update.message.reply_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

# ============================================
# 📚 توضیحات فنی پایتون (رنگی و خفن)
# ============================================

COMMAND_EXPLANATIONS = {
    "قفل": {
        "title": "قفل گروه",
        "code": """class GroupLock:
    \"\"\"قفل کردن گروه برای جلوگیری از ارسال پیام\"\"\"
    
    def execute(chat_id):
        # تنظیم مجوزها
        permissions = ChatPermissions(can_send_messages=False)
        
        # اعمال قفل روی گروه
        bot.set_chat_permissions(chat_id, permissions)
        
        # خروجی نهایی
        return "✅ گروه قفل شد - فقط ادمین‌ها می‌تونن پیام بدن" """,
        "benefit": "🛡️ جلوگیری از هرج و مرج در گروه"
    },
    "بازکن": {
        "title": "باز کردن گروه",
        "code": """class GroupUnlock:
    \"\"\"باز کردن گروه برای ارسال پیام توسط همه اعضا\"\"\"
    
    def execute(chat_id):
        # تنظیم مجوزهای پیشفرض
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        
        # اعمال باز کردن قفل
        bot.set_chat_permissions(chat_id, permissions)
        
        return "✅ گروه باز شد - همه می‌تونن پیام بدن" """,
        "benefit": "🎉 بازگشت به حالت عادی گروه"
    },
    "بن": {
        "title": "بن کردن کاربر",
        "code": """class UserBan:
    \"\"\"بن کردن کامل کاربر از گروه\"\"\"
    
    def execute(chat_id, user_id, reason):
        # حذف کاربر از گروه
        bot.ban_chat_member(chat_id, user_id)
        
        # ذخیره در لاگ
        print(f"[BAN] {user_id} - {reason}")
        
        return f"✅ کاربر {user_id} بن شد" """,
        "benefit": "⚠️ حذف کاربران مخرب و اسپمر"
    },
    "آنبن": {
        "title": "آنبن کردن کاربر",
        "code": """class UserUnban:
    \"\"\"برداشتن بن از کاربر\"\"\"
    
    def execute(chat_id, user_id):
        # برداشتن محدودیت
        bot.unban_chat_member(chat_id, user_id)
        
        return f"✅ کاربر {user_id} آنبن شد" """,
        "benefit": "🔄 فرصت دوباره به کاربر"
    },
    "میوت": {
        "title": "میوت کاربر",
        "code": """class UserMute:
    \"\"\"میوت موقت کاربر با قابلیت تعیین زمان\"\"\"
    
    def execute(chat_id, user_id, duration=None):
        permissions = ChatPermissions(can_send_messages=False)
        
        if duration:
            until_date = datetime.now() + duration
            bot.restrict_chat_member(chat_id, user_id, permissions, until_date=until_date)
            return f"✅ کاربر {user_id} به مدت {duration} میوت شد"
        else:
            bot.restrict_chat_member(chat_id, user_id, permissions)
            return f"✅ کاربر {user_id} برای همیشه میوت شد" """,
        "benefit": "⏰ تنبیه موقت بدون حذف کاربر"
    },
    "آنمیوت": {
        "title": "آنمیوت کاربر",
        "code": """class UserUnmute:
    \"\"\"برداشتن میوت از کاربر\"\"\"
    
    def execute(chat_id, user_id):
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_other_messages=True
        )
        bot.restrict_chat_member(chat_id, user_id, permissions)
        
        return f"✅ کاربر {user_id} آنمیوت شد" """,
        "benefit": "🗣️ بازگشت کاربر به چرخه گفتگو"
    },
    "کیک": {
        "title": "کیک کاربر",
        "code": """class UserKick:
    \"\"\"اخراج موقت کاربر (می‌تونه دوباره بیاد)\"\"\"
    
    def execute(chat_id, user_id):
        # اخراج و آنبن فوری
        bot.ban_chat_member(chat_id, user_id)
        bot.unban_chat_member(chat_id, user_id)
        
        return f"✅ کاربر {user_id} کیک شد" """,
        "benefit": "🚪 اخطار جدی بدون حذف دائمی"
    },
    "پاکسازی": {
        "title": "پاکسازی پیام‌ها",
        "code": """class MessagePurge:
    \"\"\"پاکسازی دسته‌جمعی پیام‌های اخیر\"\"\"
    
    def execute(chat_id, count=500):
        deleted = 0
        current = get_current_message_id()
        
        for msg_id in range(current, current - count, -1):
            try:
                bot.delete_message(chat_id, msg_id)
                deleted += 1
            except:
                pass
        
        return f"✅ {deleted} پیام حذف شد" """,
        "benefit": "🧽 نظافت گروه و حذف اسپم"
    },
    "تنظیمات": {
        "title": "تنظیمات گروه",
        "code": """class GroupSettings:
    \"\"\"مدیریت تنظیمات گروه\"\"\"
    
    settings = {
        'welcome_enabled': 'فعال/غیرفعال کردن خوش‌آمدگویی',
        'delete_links': 'حذف خودکار لینک‌ها',
        'delete_spam': 'فیلتر کلمات اسپم',
    }
    
    def toggle(key):
        current = get_setting(key)
        set_setting(key, not current)
        return f"✅ {key} = {not current}" """,
        "benefit": "🎛️ شخصی‌سازی رفتار ربات"
    }
}

async def send_python_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    """ارسال توضیحات پایتون با رنگ و فرمت خفن"""
    if command not in COMMAND_EXPLANATIONS:
        return
    
    info = COMMAND_EXPLANATIONS[command]
    
    text = f"""**📚 توضیحات فنی دستور: {info['title']}**

━━━━━━━━━━━━━━━━━━━━━━
**📝 کد پایتون:**

```python
{info['code']}
