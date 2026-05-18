#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v5.0 — Complete Edition
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
    "idiot", "stupid", "fool", "dumb", "asshole", "bastard"
]

warnings = {}

# ============================================
# ✨ ایموجی‌های پریمیوم (Custom Emoji IDs)
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
    "laugh2": {"id": "5920515596088250243", "char": "😂", "length": 2},
    "grin": {"id": "5233605022419270727", "char": "😁", "length": 2},
    "umbrella": {"id": "5240242851425559175", "char": "☔️", "length": 2},
    "check": {"id": "5208880351690112495", "char": "✅", "length": 1},
    "butterfly": {"id": "6037196272539011616", "char": "🦋", "length": 2},
    "cool": {"id": "5114163768623895481", "char": "🆒", "length": 2},
    "test_tube": {"id": "5294271852087100131", "char": "🧪", "length": 2},
    "ghost": {"id": "5307937750828194743", "char": "🫥", "length": 2},
    "slot": {"id": "5415683280395585071", "char": "🎰", "length": 2},
    "pen": {"id": "5931757569906314192", "char": "✍️", "length": 2},
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
        logger.error(f"خطا در send_premium: {e}")
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
        logger.error(f"خطا در reply_premium: {e}")
        return await update.message.reply_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

# ============================================
# 📚 توضیحات فنی دستورات (به زبان پایتون)
# ============================================

COMMAND_EXPLANATIONS = {
    "lock": {
        "title": "🔒 قفل گروه",
        "code": """class GroupLock:
    '''قفل کردن گروه برای جلوگیری از ارسال پیام توسط اعضا'''
    
    def execute(chat_id):
        permissions = ChatPermissions(can_send_messages=False)
        bot.set_chat_permissions(chat_id, permissions)
        
        نتیجه: فقط ادمین‌ها می‌تونن پیام بدن""",
        "benefit": "🛡️ فایده برای گروه: جلوگیری از هرج و مرج، کنترل کامل توسط ادمین‌ها"
    },
    "unlock": {
        "title": "🔓 باز کردن گروه",
        "code": """class GroupUnlock:
    '''باز کردن گروه برای ارسال پیام توسط همه اعضا'''
    
    def execute(chat_id):
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_send_polls=True
        )
        bot.set_chat_permissions(chat_id, permissions)
        
        نتیجه: همه اعضا می‌تونن پیام بدن""",
        "benefit": "🎉 فایده برای گروه: بازگشت به حالت عادی، افزایش تعامل اعضا"
    },
    "ban": {
        "title": "🚫 بن کردن کاربر",
        "code": """class UserBan:
    '''بن کردن کامل کاربر از گروه (عدم امکان بازگشت)'''
    
    def execute(chat_id, user_id, reason):
        bot.ban_chat_member(chat_id, user_id)
        
        نتیجه: کاربر دیگه نمیتونه به گروه ملحق بشه""",
        "benefit": "⚠️ فایده برای گروه: حذف کاربران مخرب، اسپمرها و مزاحمان"
    },
    "unban": {
        "title": "✅ آنبن کردن کاربر",
        "code": """class UserUnban:
    '''برداشتن بن از کاربر و اجازه بازگشت'''
    
    def execute(chat_id, user_id):
        bot.unban_chat_member(chat_id, user_id)
        
        نتیجه: کاربر می‌تونه دوباره به گروه ملحق بشه""",
        "benefit": "🔄 فایده برای گروه: فرصت دوباره به کاربرانی که اشتباه کردن"
    },
    "mute": {
        "title": "🔇 میوت کردن کاربر",
        "code": """class UserMute:
    '''سکوت موقت کاربر (میوت) با قابلیت تعیین زمان'''
    
    def execute(chat_id, user_id, duration=None):
        permissions = ChatPermissions(can_send_messages=False)
        
        if duration:
            until_date = datetime.now() + duration
            bot.restrict_chat_member(chat_id, user_id, permissions, until_date=until_date)
        else:
            bot.restrict_chat_member(chat_id, user_id, permissions)
        
        نتیجه: کاربر می‌تونه گروه رو ببینه ولی نتونه پیام بفرسته""",
        "benefit": "⏰ فایده برای گروه: تنبیه موقت بدون حذف کاربر، قابل تنظیم با زمان"
    },
    "unmute": {
        "title": "🔊 آنمیوت کردن کاربر",
        "code": """class UserUnmute:
    '''برداشتن میوت از کاربر'''
    
    def execute(chat_id, user_id):
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        bot.restrict_chat_member(chat_id, user_id, permissions)
        
        نتیجه: کاربر می‌تونه دوباره پیام بفرسته""",
        "benefit": "🗣️ فایده برای گروه: بازگشت کاربر به چرخه گفتگو"
    },
    "kick": {
        "title": "👢 کیک کردن کاربر",
        "code": """class UserKick:
    '''اخراج موقت کاربر (می‌تونه دوباره بیاد)'''
    
    def execute(chat_id, user_id):
        bot.ban_chat_member(chat_id, user_id)
        bot.unban_chat_member(chat_id, user_id)
        
        نتیجه: کاربر از گروه خارج میشه ولی می‌تونه دوباره بیاد""",
        "benefit": "🚪 فایده برای گروه: اخطار جدی بدون حذف دائمی"
    },
    "purge": {
        "title": "🧹 پاکسازی پیام‌ها",
        "code": """class MessagePurge:
    '''پاکسازی دسته‌جمعی پیام‌های اخیر'''
    
    def execute(chat_id, message_count=500):
        deleted = 0
        current_msg_id = get_current_message_id()
        
        for msg_id in range(current_msg_id, current_msg_id - message_count, -1):
            try:
                bot.delete_message(chat_id, msg_id)
                deleted += 1
            except:
                pass
        
        نتیجه: پیام‌های غیرضروری پاک میشن""",
        "benefit": "🧽 فایده برای گروه: نظافت گروه، حذف اسپم و پیام‌های تکراری"
    },
    "settings": {
        "title": "⚙️ تنظیمات گروه",
        "code": """class GroupSettings:
    '''مدیریت تنظیمات گروه مانند ولکام، آنتی‌اسپم و ...'''
    
    settings = {
        'welcome_enabled': 'فعال/غیرفعال کردن پیام خوش‌آمدگویی',
        'delete_links': 'حذف خودکار لینک‌ها',
        'delete_spam': 'فیلتر کلمات اسپم',
        'delete_stickers': 'حذف استیکرها'
    }
    
    def toggle_setting(key):
        current = get_setting(chat_id, key)
        set_setting(chat_id, key, not current)
        
        نتیجه: تنظیمات مطابق نیاز گروه تغییر می‌کنه""",
        "benefit": "🎛️ فایده برای گروه: شخصی‌سازی رفتار ربات بر اساس نیاز گروه"
    }
}

async def send_command_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    """ارسال توضیحات فنی دستور به صورت کد پایتون در گروه"""
    if command not in COMMAND_EXPLANATIONS:
        return
    
    info = COMMAND_EXPLANATIONS[command]
    
    text = f"""
📚 **توضیحات فنی دستور: {info['title']}**

━━━━━━━━━━━━━━━━━━━━━━
📝 **کد پایتون:**
