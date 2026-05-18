#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v6.0 — Dark Code Edition
# ============================================

import asyncio
import logging
import re
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

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

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")

SUDO_USERS = list(map(int, os.getenv("SUDO_USERS", "").split(","))) if os.getenv("SUDO_USERS") else []
FORCE_SUB_CHANNELS = os.getenv("FORCE_SUB_CHANNELS", "https://t.me/dontworry80").split(",")
FORCE_SUB_IDS = list(map(int, os.getenv("FORCE_SUB_IDS", "0").split(","))) if os.getenv("FORCE_SUB_IDS") else [0]
GOODBYE_DEFAULT = "😢 {mention} از گروه خارج شد!"

FORCE_SUB_CHANNEL = FORCE_SUB_CHANNELS[0] if FORCE_SUB_CHANNELS else "https://t.me/dontworry80"
FORCE_SUB_USERNAME = "@dontworry80"

SPAM_KEYWORDS = ["join", "fast", "سایت", "🔞", "💰", "کلیک", "عضویت"]
FORBIDDEN_DOMAINS = ["bit.ly", "tinyurl.com", "t.me/+"]

BAD_WORDS = [
    "احمق", "خر", "گاو", "کودن", "نادان", "بی‌شعور", "بیشعور",
    "ابله", "حیوان", "مادرجنده", "کصکش", "کیر", "کون", "جنده",
    "اوبی", "عوضی", "بی‌ناموس", "بیناموس", "الاغ", "خفه",
]

warnings = {}

# ============================================
# Premium Emojis
# ============================================

CUSTOM_EMOJIS = {
    "heart_blue": {"id": "5377688663960331522", "char": "💙", "length": 2},
    "heart_red": {"id": "5370897968478047651", "char": "❤️", "length": 2},
    "earth": {"id": "5377357058125340868", "char": "🌎", "length": 2},
    "grin": {"id": "5233605022419270727", "char": "😁", "length": 2},
    "cool": {"id": "5114163768623895481", "char": "🆒", "length": 2},
    "check": {"id": "5208880351690112495", "char": "✅", "length": 1},
}

def get_premium_prefix() -> Tuple[str, list]:
    emoji_list = [CUSTOM_EMOJIS["grin"], CUSTOM_EMOJIS["heart_red"], CUSTOM_EMOJIS["heart_blue"], CUSTOM_EMOJIS["earth"], CUSTOM_EMOJIS["cool"]]
    text = ""
    entities = []
    offset = 0
    for emoji in emoji_list:
        text += emoji["char"]
        entities.append(MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=offset, length=emoji["length"], custom_emoji_id=emoji["id"]))
        offset += emoji["length"]
    return text + "\n", entities

async def reply_premium(update: Update, text: str, context: ContextTypes.DEFAULT_TYPE, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    prefix, prefix_entities = get_premium_prefix()
    full_text = prefix + text
    try:
        return await update.message.reply_text(full_text, entities=prefix_entities, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        return await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)

# ============================================
# DARK CODE EXPLANATIONS - Real Python Code
# ============================================

def get_dark_code_block(code: str, language: str = "python") -> str:
    """Generate dark-themed code block with proper formatting"""
    return f"```{language}\n{code}\n```"

# Lock Command Code
LOCK_CODE = '''import asyncio
from typing import Optional, Dict, Any
from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

class GroupLockManager:
    """
    مدیریت قفل گروه - کلاس حرفه‌ای برای کنترل مجوزها
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def lock_group(
        self,
        chat_id: int,
        admin_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        قفل کردن گروه و جلوگیری از ارسال پیام توسط اعضا
        
        Args:
            chat_id: آیدی گروه
            admin_id: آیدی ادمین
            reason: دلیل قفل
        
        Returns:
            dict: نتیجه عملیات
        """
        result = {
            "success": False,
            "message": "",
            "chat_id": chat_id,
            "admin_id": admin_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            permissions = ChatPermissions(can_send_messages=False)
            await self.bot.set_chat_permissions(chat_id, permissions)
            
            self.logger.info(f"Group {chat_id} locked by {admin_id}")
            
            result["success"] = True
            result["message"] = "✅ گروه قفل شد"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔒 گروه قفل شد!\n👮 ادمین: {admin_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Lock failed: {e}")
            result["message"] = f"❌ خطا: {e}"
            raise
        
        return result

# استفاده در هندلر
async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    manager = GroupLockManager(context.bot)
    result = await manager.lock_group(update.effective_chat.id, update.effective_user.id)
    await update.message.reply_text(result["message"])
'''

# Unlock Command Code
UNLOCK_CODE = '''import asyncio
from typing import Optional, Dict, Any
from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

class GroupUnlockManager:
    """
    مدیریت باز کردن قفل گروه - کلاس حرفه‌ای
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self._default_permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_send_polls=True
        )
    
    async def unlock_group(
        self,
        chat_id: int,
        admin_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        باز کردن قفل گروه و بازگرداندن مجوزها
        
        Args:
            chat_id: آیدی گروه
            admin_id: آیدی ادمین
            reason: دلیل باز کردن قفل
        
        Returns:
            dict: نتیجه عملیات
        """
        result = {
            "success": False,
            "message": "",
            "chat_id": chat_id,
            "admin_id": admin_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self.bot.set_chat_permissions(chat_id, self._default_permissions)
            
            self.logger.info(f"Group {chat_id} unlocked by {admin_id}")
            
            result["success"] = True
            result["message"] = "✅ گروه باز شد"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔓 گروه باز شد!\n👮 ادمین: {admin_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Unlock failed: {e}")
            result["message"] = f"❌ خطا: {e}"
            raise
        
        return result

async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manager = GroupUnlockManager(context.bot)
    result = await manager.unlock_group(update.effective_chat.id, update.effective_user.id)
    await update.message.reply_text(result["message"])
'''

# Ban Command Code
BAN_CODE = '''import asyncio
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

class UserBanManager:
    """
    مدیریت بن کردن کاربران - کلاس حرفه‌ای
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def ban_user(
        self,
        chat_id: int,
        user_id: int,
        admin_id: int,
        reason: str = "بدون دلیل"
    ) -> Dict[str, Any]:
        """
        بن کردن کاربر از گروه (عدم امکان بازگشت)
        
        Args:
            chat_id: آیدی گروه
            user_id: آیدی کاربر مورد نظر
            admin_id: آیدی ادمین
            reason: دلیل بن
        
        Returns:
            dict: نتیجه عملیات
        """
        result = {
            "success": False,
            "message": "",
            "user_id": user_id,
            "admin_id": admin_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await self.bot.ban_chat_member(chat_id, user_id)
            
            self.logger.warning(f"User {user_id} banned in {chat_id} by {admin_id} | Reason: {reason}")
            
            result["success"] = True
            result["message"] = f"✅ کاربر {user_id} بن شد"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 کاربر بن شد!\n👮 ادمین: {admin_id}\n📌 دلیل: {reason}"
            )
            
        except Exception as e:
            self.logger.error(f"Ban failed: {e}")
            result["message"] = f"❌ خطا: {e}"
            raise
        
        return result

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target_user(update)
    if not target:
        return
    manager = UserBanManager(context.bot)
    result = await manager.ban_user(
        update.effective_chat.id,
        target.id,
        update.effective_user.id
    )
    await update.message.reply_text(result["message"])
'''

# Mute Command Code
MUTE_CODE = '''import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

class UserMuteManager:
    """
    مدیریت میوت کردن کاربران - با قابلیت زمان‌بندی
    """
    
    TIME_UNITS = {
        "s": "seconds",
        "m": "minutes", 
        "h": "hours",
        "d": "days"
    }
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    def parse_duration(self, time_str: str) -> Optional[timedelta]:
        """
        تبدیل رشته زمانی به timedelta
        مثال: "1h" -> 1 ساعت, "30m" -> 30 دقیقه
        """
        match = re.match(r"(\d+)([smhd])", time_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit == "s":
                return timedelta(seconds=value)
            elif unit == "m":
                return timedelta(minutes=value)
            elif unit == "h":
                return timedelta(hours=value)
            elif unit == "d":
                return timedelta(days=value)
        return None
    
    async def mute_user(
        self,
        chat_id: int,
        user_id: int,
        admin_id: int,
        duration: Optional[timedelta] = None,
        reason: str = "بدون دلیل"
    ) -> Dict[str, Any]:
        """
        میوت کردن کاربر (سکوت موقت یا دائم)
        
        Args:
            chat_id: آیدی گروه
            user_id: آیدی کاربر
            admin_id: آیدی ادمین
            duration: مدت زمان میوت (None = دائم)
            reason: دلیل میوت
        
        Returns:
            dict: نتیجه عملیات
        """
        result = {
            "success": False,
            "message": "",
            "user_id": user_id,
            "admin_id": admin_id,
            "duration": duration.total_seconds() if duration else None,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            permissions = ChatPermissions(can_send_messages=False)
            until_date = datetime.now() + duration if duration else None
            
            await self.bot.restrict_chat_member(
                chat_id, user_id,
                permissions=permissions,
                until_date=until_date
            )
            
            duration_text = f" به مدت {duration}" if duration else " برای همیشه"
            self.logger.info(f"User {user_id} muted{duration_text} in {chat_id} by {admin_id}")
            
            result["success"] = True
            result["message"] = f"✅ کاربر میوت شد{duration_text}"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔇 کاربر میوت شد{duration_text}!\n👮 ادمین: {admin_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Mute failed: {e}")
            result["message"] = f"❌ خطا: {e}"
            raise
        
        return result

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target_user(update)
    if not target:
        return
    manager = UserMuteManager(context.bot)
    duration = manager.parse_duration(context.args[0]) if context.args else None
    result = await manager.mute_user(
        update.effective_chat.id,
        target.id,
        update.effective_user.id,
        duration
    )
    await update.message.reply_text(result["message"])
'''

# Kick Command Code
KICK_CODE = '''import asyncio
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

class UserKickManager:
    """
    مدیریت کیک کردن کاربران - اخراج موقت
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def kick_user(
        self,
        chat_id: int,
        user_id: int,
        admin_id: int,
        reason: str = "بدون دلیل"
    ) -> Dict[str, Any]:
        """
        کیک کردن کاربر (اخراج موقت - می‌تواند دوباره بیاید)
        
        Args:
            chat_id: آیدی گروه
            user_id: آیدی کاربر
            admin_id: آیدی ادمین
            reason: دلیل کیک
        
        Returns:
            dict: نتیجه عملیات
        """
        result = {
            "success": False,
            "message": "",
            "user_id": user_id,
            "admin_id": admin_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # بن کردن
            await self.bot.ban_chat_member(chat_id, user_id)
            # بلافاصله آنبن کردن برای امکان بازگشت
            await self.bot.unban_chat_member(chat_id, user_id)
            
            self.logger.info(f"User {user_id} kicked from {chat_id} by {admin_id}")
            
            result["success"] = True
            result["message"] = f"✅ کاربر کیک شد"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"👢 کاربر کیک شد!\n👮 ادمین: {admin_id}\n📌 دلیل: {reason}"
            )
            
        except Exception as e:
            self.logger.error(f"Kick failed: {e}")
            result["message"] = f"❌ خطا: {e}"
            raise
        
        return result

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target_user(update)
    if not target:
        return
    manager = UserKickManager(context.bot)
    result = await manager.kick_user(
        update.effective_chat.id,
        target.id,
        update.effective_user.id
    )
    await update.message.reply_text(result["message"])
'''

# Purge Command Code
PURGE_CODE = '''import asyncio
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes

class MessagePurgeManager:
    """
    مدیریت پاکسازی پیام‌ها - حذف دسته‌جمعی
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def purge_messages(
        self,
        chat_id: int,
        admin_id: int,
        limit: int = 300
    ) -> Dict[str, Any]:
        """
        پاکسازی پیام‌های اخیر
        
        Args:
            chat_id: آیدی گروه
            admin_id: آیدی ادمین
            limit: تعداد پیام‌های حذفی
        
        Returns:
            dict: نتیجه عملیات شامل تعداد پیام‌های حذف شده
        """
        result = {
            "success": False,
            "deleted_count": 0,
            "chat_id": chat_id,
            "admin_id": admin_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # دریافت آخرین message_id
            current_msg_id = await self._get_current_message_id(chat_id)
            deleted = 0
            
            for msg_id in range(current_msg_id, max(current_msg_id - limit, 1), -1):
                try:
                    await self.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted += 1
                    await asyncio.sleep(0.05)  # جلوگیری از rate limit
                except:
                    pass
            
            self.logger.info(f"Purged {deleted} messages in {chat_id} by {admin_id}")
            
            result["success"] = True
            result["deleted_count"] = deleted
            result["message"] = f"✅ {deleted} پیام حذف شد"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🧹 پاکسازی کامل شد!\n🗑 {deleted} پیام حذف شد.\n👮 ادمین: {admin_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Purge failed: {e}")
            result["message"] = f"❌ خطا: {e}"
            raise
        
        return result
    
    async def _get_current_message_id(self, chat_id: int) -> int:
        """دریافت آخرین message_id گروه"""
        try:
            # روش جایگزین برای دریافت message_id
            return int(datetime.now().timestamp())
        except:
            return 10000

async def purge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manager = MessagePurgeManager(context.bot)
    result = await manager.purge_messages(
        update.effective_chat.id,
        update.effective_user.id
    )
    await update.message.reply_text(result["message"])
'''

# Settings Command Code
SETTINGS_CODE = '''import asyncio
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class GroupSettingsManager:
    """
    مدیریت تنظیمات گروه - ذخیره و بازیابی در دیتابیس
    """
    
    DEFAULT_SETTINGS = {
        "welcome_enabled": 1,
        "goodbye_enabled": 1,
        "delete_links": 1,
        "delete_spam": 1,
        "delete_stickers": 0
    }
    
    SETTINGS_NAMES = {
        "welcome_enabled": "📝 ولکام (خوش‌آمدگویی)",
        "goodbye_enabled": "👋 خداحافظی",
        "delete_links": "🔗 حذف لینک",
        "delete_spam": "🚫 آنتی اسپم",
        "delete_stickers": "🎴 حذف استیکر"
    }
    
    def __init__(self, db):
        self.db = db
    
    def get_setting(self, chat_id: int, key: str) -> int:
        """دریافت یک تنظیم از دیتابیس"""
        cur = self.db.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key=?",
            (chat_id, key)
        )
        row = cur.fetchone()
        return row[0] if row else self.DEFAULT_SETTINGS.get(key, 0)
    
    def set_setting(self, chat_id: int, key: str, value: int) -> bool:
        """ذخیره یک تنظیم در دیتابیس"""
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, ?, ?)",
                (chat_id, key, value)
            )
            self.db.commit()
            return True
        except:
            return False
    
    def get_all_settings(self, chat_id: int) -> Dict[str, int]:
        """دریافت همه تنظیمات یک گروه"""
        result = {}
        for key in self.DEFAULT_SETTINGS.keys():
            result[key] = self.get_setting(chat_id, key)
        return result
    
    def build_keyboard(self, chat_id: int) -> InlineKeyboardMarkup:
        """ساخت صفحه کلید تنظیمات"""
        settings = self.get_all_settings(chat_id)
        buttons = []
        
        for key, name in self.SETTINGS_NAMES.items():
            status = "✅" if settings.get(key, 1) else "❌"
            buttons.append([InlineKeyboardButton(
                f"{status} {name}",
                callback_data=f"toggle_{key}"
            )])
        
        buttons.append([InlineKeyboardButton("❌ بستن", callback_data="close_settings")])
        
        return InlineKeyboardMarkup(buttons)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    manager = GroupSettingsManager(get_db())
    await update.message.reply_text(
        "⚙️ پنل تنظیمات گروه\n\nهر گزینه را برای تغییر وضعیت لمس کنید:",
        reply_markup=manager.build_keyboard(update.effective_chat.id)
    )
'''

# ============================================
# Command Explanations Dictionary
# ============================================

COMMAND_EXPLANATIONS = {
    "lock": {
        "title": "🔒 قفل گروه",
        "code": LOCK_CODE,
        "benefit": "🛡️ جلوگیری از هرج و مرج در گروه - فقط ادمین‌ها می‌تونن پیام بدن"
    },
    "unlock": {
        "title": "🔓 باز کردن گروه",
        "code": UNLOCK_CODE,
        "benefit": "🎉 بازگشت به حالت عادی - همه اعضا می‌تونن پیام بدن"
    },
    "ban": {
        "title": "🚫 بن کردن کاربر",
        "code": BAN_CODE,
        "benefit": "⚠️ حذف کامل کاربر از گروه - کاربر نمی‌تونه دوباره بیاد"
    },
    "mute": {
        "title": "🔇 میوت کاربر",
        "code": MUTE_CODE,
        "benefit": "⏰ تنبیه موقت - کاربر می‌تونه گروه رو ببینه ولی پیام بفرسته"
    },
    "kick": {
        "title": "👢 کیک کاربر",
        "code": KICK_CODE,
        "benefit": "🚪 اخطار جدی - کاربر اخراج میشه ولی می‌تونه دوباره بیاد"
    },
    "purge": {
        "title": "🧹 پاکسازی پیام‌ها",
        "code": PURGE_CODE,
        "benefit": "🧽 نظافت گروه - حذف خودکار پیام‌های قدیمی و اسپم"
    },
    "settings": {
        "title": "⚙️ تنظیمات گروه",
        "code": SETTINGS_CODE,
        "benefit": "🎛️ شخصی‌سازی رفتار ربات - فعال/غیرفعال کردن قابلیت‌ها"
    }
}

async def send_python_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    """ارسال توضیحات فنی با کد پایتون واقعی و رنگ تیره"""
    if command not in COMMAND_EXPLANATIONS:
        return
    
    info = COMMAND_EXPLANATIONS[command]
    
    text = f"""📚 **توضیحات فنی دستور: {info['title']}**

━━━━━━━━━━━━━━━━━━━━━━
📝 **کد پایتون (Dark Mode):**

```python
{info['code'][:1500]}
