#!/usr/bin/env python3
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

BAD_WORDS = ["احمق", "خر", "گاو", "کودن", "نادان", "بی‌شعور", "ابله", "حیوان", "مادرجنده", "کصکش", "کیر", "کون", "جنده", "الاغ"]

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
}

def get_premium_prefix():
    emoji_list = [CUSTOM_EMOJIS["grin"], CUSTOM_EMOJIS["heart_red"], CUSTOM_EMOJIS["heart_blue"], CUSTOM_EMOJIS["earth"], CUSTOM_EMOJIS["cool"]]
    text = ""
    entities = []
    offset = 0
    for emoji in emoji_list:
        text += emoji["char"]
        entities.append(MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=offset, length=emoji["length"], custom_emoji_id=emoji["id"]))
        offset += emoji["length"]
    return text + "\n", entities

async def reply_premium(update, text, context, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    prefix, prefix_entities = get_premium_prefix()
    full_text = prefix + text
    try:
        return await update.message.reply_text(full_text, entities=prefix_entities, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        return await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)

# ============================================
# Python Code for Each Command
# ============================================

LOCK_PYTHON_CODE = '''class GroupLock:
    """قفل کردن گروه - فقط ادمین‌ها می‌تونن پیام بدن"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, chat_id: int, admin_id: int) -> dict:
        try:
            permissions = ChatPermissions(can_send_messages=False)
            await self.bot.set_chat_permissions(chat_id, permissions)
            self.logger.info(f"Group {chat_id} locked by {admin_id}")
            return {"success": True, "message": "گروه قفل شد"}
        except Exception as e:
            self.logger.error(f"Lock failed: {e}")
            return {"success": False, "message": str(e)}'''

UNLOCK_PYTHON_CODE = '''class GroupUnlock:
    """باز کردن گروه - همه اعضا می‌تونن پیام بدن"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, chat_id: int, admin_id: int) -> dict:
        try:
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            await self.bot.set_chat_permissions(chat_id, permissions)
            self.logger.info(f"Group {chat_id} unlocked by {admin_id}")
            return {"success": True, "message": "گروه باز شد"}
        except Exception as e:
            self.logger.error(f"Unlock failed: {e}")
            return {"success": False, "message": str(e)}'''

BAN_PYTHON_CODE = '''class UserBan:
    """بن کردن کاربر - حذف کامل از گروه"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int, reason: str = "") -> dict:
        try:
            await self.bot.ban_chat_member(chat_id, user_id)
            self.logger.warning(f"User {user_id} banned in {chat_id} by {admin_id}")
            return {"success": True, "message": f"کاربر {user_id} بن شد"}
        except Exception as e:
            self.logger.error(f"Ban failed: {e}")
            return {"success": False, "message": str(e)}'''

MUTE_PYTHON_CODE = '''class UserMute:
    """میوت کاربر - سکوت موقت با قابلیت زمان‌بندی"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    def parse_time(self, time_str: str):
        match = re.match(r"(\\d+)([smhd])", time_str)
        if match:
            val, unit = int(match.group(1)), match.group(2)
            units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            return val * units.get(unit, 1)
        return None
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int, duration_str: str = None) -> dict:
        try:
            permissions = ChatPermissions(can_send_messages=False)
            until_date = None
            if duration_str:
                seconds = self.parse_time(duration_str)
                if seconds:
                    until_date = datetime.now() + timedelta(seconds=seconds)
            await self.bot.restrict_chat_member(chat_id, user_id, permissions=permissions, until_date=until_date)
            self.logger.info(f"User {user_id} muted in {chat_id} by {admin_id}")
            return {"success": True, "message": f"کاربر {user_id} میوت شد"}
        except Exception as e:
            self.logger.error(f"Mute failed: {e}")
            return {"success": False, "message": str(e)}'''

UNMUTE_PYTHON_CODE = '''class UserUnmute:
    """آنمیوت کاربر - برداشتن سکوت"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int) -> dict:
        try:
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            await self.bot.restrict_chat_member(chat_id, user_id, permissions=permissions)
            self.logger.info(f"User {user_id} unmuted in {chat_id} by {admin_id}")
            return {"success": True, "message": f"کاربر {user_id} آنمیوت شد"}
        except Exception as e:
            self.logger.error(f"Unmute failed: {e}")
            return {"success": False, "message": str(e)}'''

KICK_PYTHON_CODE = '''class UserKick:
    """کیک کاربر - اخراج موقت از گروه"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int) -> dict:
        try:
            await self.bot.ban_chat_member(chat_id, user_id)
            await self.bot.unban_chat_member(chat_id, user_id)
            self.logger.info(f"User {user_id} kicked from {chat_id} by {admin_id}")
            return {"success": True, "message": f"کاربر {user_id} کیک شد"}
        except Exception as e:
            self.logger.error(f"Kick failed: {e}")
            return {"success": False, "message": str(e)}'''

PURGE_PYTHON_CODE = '''class MessagePurge:
    """پاکسازی پیام‌ها - حذف دسته‌جمعی"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, chat_id: int, admin_id: int, limit: int = 300) -> dict:
        try:
            current = datetime.now().timestamp()
            deleted = 0
            for msg_id in range(int(current), int(current) - limit, -1):
                try:
                    await self.bot.delete_message(chat_id, msg_id)
                    deleted += 1
                except:
                    pass
                await asyncio.sleep(0.05)
            self.logger.info(f"Purged {deleted} messages in {chat_id} by {admin_id}")
            return {"success": True, "deleted": deleted, "message": f"{deleted} پیام حذف شد"}
        except Exception as e:
            self.logger.error(f"Purge failed: {e}")
            return {"success": False, "message": str(e)}'''

SETTINGS_PYTHON_CODE = '''class GroupSettings:
    """تنظیمات گروه - ذخیره در دیتابیس"""
    
    DEFAULTS = {
        "welcome_enabled": 1,
        "goodbye_enabled": 1,
        "delete_links": 1,
        "delete_spam": 1,
        "delete_stickers": 0
    }
    
    def __init__(self, db):
        self.db = db
    
    def get(self, chat_id: int, key: str) -> int:
        cur = self.db.execute("SELECT value FROM settings WHERE chat_id=? AND key=?", (chat_id, key))
        row = cur.fetchone()
        return row[0] if row else self.DEFAULTS.get(key, 0)
    
    def set(self, chat_id: int, key: str, value: int) -> bool:
        try:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (?, ?, ?)", (chat_id, key, value))
            self.db.commit()
            return True
        except:
            return False
    
    def get_all(self, chat_id: int) -> dict:
        return {key: self.get(chat_id, key) for key in self.DEFAULTS}'''

# ============================================
# Send Python Code Explanation
# ============================================

async def send_code_explanation(update, context, code, title):
    text = f"📚 **توضیحات فنی دستور: {title}**\n\n━━━━━━━━━━━━━━━━━━━━━━\n📝 **کد پایتون:**\n\n```python\n{code}\n```"
    await reply_premium(update, text, context)

# ============================================
# Force Subscribe
# ============================================

async def is_force_subscribed(user_id, context):
    for ch_id in FORCE_SUB_IDS:
        if ch_id == 0:
            continue
        try:
            member = await context.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                return False
        except:
            return False
    return True

async def force_sub_panel(update, context):
    user = update.effective_user
    if await is_force_subscribed(user.id, context):
        await reply_premium(update, "✅ عضویت تأیید شد! به گروه خوش اومدی 🎉", context)
        return
    buttons = [[InlineKeyboardButton("📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)], [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_sub")]]
    await reply_premium(update, f"🔒 برای استفاده از ربات باید عضو کانال {FORCE_SUB_USERNAME} بشی:", context, reply_markup=InlineKeyboardMarkup(buttons))

async def check_sub_callback(update, context):
    query = update.callback_query
    await query.answer()
    if await is_force_subscribed(query.from_user.id, context):
        await query.edit_message_text("✅ عضویت تأیید شد!")
    else:
        await query.answer("❌ هنوز عضو نشدی!", show_alert=True)

# ============================================
# Welcome & Goodbye
# ============================================

welcome_counter = {}

async def welcome_member(update, context):
    if not update.message or not update.message.new_chat_members:
        return
    chat_id = update.effective_chat.id
    if not get_setting(chat_id, "welcome_enabled", 1):
        return
    if chat_id not in welcome_counter:
        welcome_counter[chat_id] = 0
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        welcome_counter[chat_id] += 1
        greeting = "خوش اومدی 🤗" if welcome_counter[chat_id] % 2 == 1 else "خوش اومدی 😊"
        text = f"👤 **{member.first_name}**\n🆔 `{member.id}`\n👋 {greeting}"
        try:
            await reply_premium(update, text, context)
        except:
            pass

async def goodbye_member(update, context):
    if not update.message or not update.message.left_chat_member:
        return
    chat_id = update.effective_chat.id
    if not get_setting(chat_id, "goodbye_enabled", 1):
        return
    member = update.message.left_chat_member
    mention = f"[{member.first_name}](tg://user?id={member.id})"
    text = get_setting(chat_id, "goodbye_text") or GOODBYE_DEFAULT
    text = text.replace("{mention}", mention)
    try:
        await reply_premium(update, text, context)
    except:
        pass

# ============================================
# Anti Bad Words & Anti Spam
# ============================================

async def anti_bad_words(update, context):
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    msg_text = update.message.text.lower()
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except:
        pass
    for word in BAD_WORDS:
        if word in msg_text:
            key = (chat_id, user_id)
            warnings[key] = warnings.get(key, 0) + 1
            count = warnings[key]
            if count >= 5:
                try:
                    await context.bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now() + timedelta(hours=24))
                    await reply_premium(update, f"🔇 {update.effective_user.first_name} بعد از ۵ اخطار سکوت شد!", context)
                    warnings[key] = 0
                except:
                    pass
            else:
                await reply_premium(update, f"⚠️ {update.effective_user.first_name} اخطار {count}/5", context)
            await update.message.delete()
            return

async def anti_spam(update, context):
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    msg_text = update.message.text.lower()
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except:
        pass
    if get_setting(chat_id, "delete_links", 1):
        for domain in FORBIDDEN_DOMAINS:
            if domain in msg_text:
                await update.message.delete()
                await reply_premium(update, f"⚠️ {update.effective_user.first_name} لینک ممنوع ارسال کرد!", context)
                return
    if get_setting(chat_id, "delete_spam", 1):
        for word in SPAM_KEYWORDS:
            if word in msg_text:
                await update.message.delete()
                return
    await anti_bad_words(update, context)

# ============================================
# Admin Check
# ============================================

async def is_admin(update, context):
    user_id = update.effective_user.id
    if user_id in SUDO_USERS:
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

def get_target_user(update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None

# ============================================
# Command Handlers
# ============================================

async def lock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=False))
        await reply_premium(update, "🔒 گروه قفل شد! فقط ادمین‌ها می‌تونن پیام بدن.", context)
        await send_code_explanation(update, context, LOCK_PYTHON_CODE, "🔒 قفل گروه")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unlock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True))
        await reply_premium(update, "🔓 گروه باز شد! همه می‌تونن پیام بدن.", context)
        await send_code_explanation(update, context, UNLOCK_PYTHON_CODE, "🔓 باز کردن گروه")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def ban_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = get_target_user(update)
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await reply_premium(update, f"🚫 **{target.first_name}** بن شد!", context)
        await send_code_explanation(update, context, BAN_PYTHON_CODE, "🚫 بن کردن کاربر")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unban_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = get_target_user(update)
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await reply_premium(update, f"✅ **{target.first_name}** آنبن شد!", context)
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def mute_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = get_target_user(update)
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن\nمثال: /mute 1h", context)
        return
    duration = context.args[0] if context.args else None
    try:
        if duration:
            match = re.match(r"(\d+)([smhd])", duration)
            if match:
                val, unit = int(match.group(1)), match.group(2)
                units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
                seconds = val * units.get(unit, 1)
                until = datetime.now() + timedelta(seconds=seconds)
                await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
                await reply_premium(update, f"🔇 **{target.first_name}** میوت شد برای {duration}!", context)
            else:
                await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
                await reply_premium(update, f"🔇 **{target.first_name}** میوت دائمی شد!", context)
        else:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
            await reply_premium(update, f"🔇 **{target.first_name}** میوت دائمی شد!", context)
        await send_code_explanation(update, context, MUTE_PYTHON_CODE, "🔇 میوت کاربر")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unmute_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = get_target_user(update)
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await reply_premium(update, f"🔊 **{target.first_name}** آنمیوت شد!", context)
        await send_code_explanation(update, context, UNMUTE_PYTHON_CODE, "🔊 آنمیوت کاربر")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def kick_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = get_target_user(update)
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await reply_premium(update, f"👢 **{target.first_name}** کیک شد!", context)
        await send_code_explanation(update, context, KICK_PYTHON_CODE, "👢 کیک کاربر")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def purge_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    chat_id = update.effective_chat.id
    current = update.message.message_id
    deleted = 0
    await reply_premium(update, "🧹 در حال پاکسازی...", context)
    for msg_id in range(current, max(current - 200, 1), -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except:
            pass
        await asyncio.sleep(0.05)
    await reply_premium(update, f"✅ پاکسازی تموم شد! {deleted} پیام حذف شد.", context)
    await send_code_explanation(update, context, PURGE_PYTHON_CODE, "🧹 پاکسازی پیام‌ها")

async def purge_user_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    if not update.message.reply_to_message:
        await reply_premium(update, "❌ روی پیام کاربر reply کن", context)
        return
    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    current = update.message.message_id
    deleted = 0
    for msg_id in range(current, max(current - 200, 1), -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except:
            pass
        await asyncio.sleep(0.05)
    await reply_premium(update, f"✅ {deleted} پیام از {target.first_name} حذف شد.", context)

# ============================================
# Settings
# ============================================

def build_settings_keyboard(chat_id):
    def btn(label, key):
        val = get_setting(chat_id, key, 1)
        return InlineKeyboardButton(f"{'✅' if val else '❌'} {label}", callback_data=f"toggle_{key}")
    return InlineKeyboardMarkup([
        [btn("ولکام", "welcome_enabled")],
        [btn("خداحافظی", "goodbye_enabled")],
        [btn("حذف لینک", "delete_links")],
        [btn("آنتی اسپم", "delete_spam")],
        [btn("حذف استیکر", "delete_stickers")],
        [InlineKeyboardButton("❌ بستن", callback_data="close_settings")],
    ])

async def settings_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    await reply_premium(update, "⚙️ تنظیمات گروه", context, reply_markup=build_settings_keyboard(update.effective_chat.id))
    await send_code_explanation(update, context, SETTINGS_PYTHON_CODE, "⚙️ تنظیمات گروه")

async def settings_callback(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if query.data == "close_settings":
        await query.message.delete()
        return
    if query.data.startswith("toggle_"):
        key = query.data.replace("toggle_", "")
        current = get_setting(chat_id, key, 1)
        set_setting(chat_id, key, 0 if current else 1)
        await query.edit_message_reply_markup(reply_markup=build_settings_keyboard(chat_id))

# ============================================
# Help & Start
# ============================================

def get_help_text():
    return """
📋 **راهنمای ربات یاشا**

━━━━━━━━━━━━━━━━━━━━━━
👮 **دستورات مدیریتی**
━━━━━━━━━━━━━━━━━━━━━━

🔒 /lock - قفل کردن گروه
🔓 /unlock - باز کردن گروه
🚫 /ban - بن کردن کاربر
✅ /unban - آنبن کردن کاربر
🔇 /mute - میوت کاربر
🔊 /unmute - آنمیوت کاربر
👢 /kick - کیک کردن کاربر

━━━━━━━━━━━━━━━━━━━━━━
🧹 **دستورات پاکسازی**
━━━━━━━━━━━━━━━━━━━━━━

🗑 /purge - پاک کردن پیام‌های اخیر
👤 /purgeuser - پاک کردن پیام‌های یک کاربر

━━━━━━━━━━━━━━━━━━━━━━
⚙️ **دستورات عمومی**
━━━━━━━━━━━━━━━━━━━━━━

🎯 /start - منوی اصلی
❓ /help - راهنما
⚙️ /settings - تنظیمات گروه
📢 /join - بررسی عضویت

━━━━━━━━━━━━━━━━━━━━━━
⏱ **نحوه استفاده از /mute**
━━━━━━━━━━━━━━━━━━━━━━

/mute 30s - 30 ثانیه
/mute 5m - 5 دقیقه
/mute 2h - 2 ساعت
/mute 1d - 1 روز
/mute - میوت دائمی

━━━━━━━━━━━━━━━━━━━━━━
💡 **نکات مهم**
━━━━━━━━━━━━━━━━━━━━━━

• برای بن، میوت، کیک روی پیام کاربر reply کنید
• بعد از هر دستور، کد پایتون نمایش داده می‌شود
"""

async def start_cmd(update, context):
    if not await is_force_subscribed(update.effective_user.id, context):
        await force_sub_panel(update, context)
        return
    buttons = [
        [InlineKeyboardButton("📋 راهنما", callback_data="menu_help")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings")],
        [InlineKeyboardButton("📢 کانال ما", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("❌ بستن", callback_data="close_menu")],
    ]
    await reply_premium(update, "🤖 **ربات مدیریت گروه یاشا**\n\nاز منوی زیر استفاده کن:", context, reply_markup=InlineKeyboardMarkup(buttons))

async def help_cmd(update, context):
    await reply_premium(update, get_help_text(), context)

async def join_cmd(update, context):
    await force_sub_panel(update, context)

async def menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "menu_help":
        await query.edit_message_text(get_help_text(), parse_mode=ParseMode.MARKDOWN)
    elif query.data == "menu_settings":
        await settings_cmd(update, context)
    elif query.data == "close_menu":
        await query.message.delete()

# ============================================
# Main
# ============================================

async def set_bot_commands(app):
    commands = [
        BotCommand("start", "منوی اصلی"),
        BotCommand("help", "راهنما"),
        BotCommand("settings", "تنظیمات گروه"),
        BotCommand("join", "بررسی عضویت"),
        BotCommand("lock", "قفل گروه"),
        BotCommand("unlock", "باز کردن گروه"),
        BotCommand("ban", "بن کاربر"),
        BotCommand("unban", "آنبن کاربر"),
        BotCommand("mute", "میوت کاربر"),
        BotCommand("unmute", "آنمیوت کاربر"),
        BotCommand("kick", "کیک کاربر"),
        BotCommand("purge", "پاکسازی پیام‌ها"),
        BotCommand("purgeuser", "پاکسازی پیام‌های کاربر"),
    ]
    await app.bot.set_my_commands(commands)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.post_init = set_bot_commands

    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("purge", purge_cmd))
    app.add_handler(CommandHandler("purgeuser", purge_user_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("join", join_cmd))

    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|close_settings)"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^(menu_)"))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))

    logger.info("ربات یاشا شروع به کار کرد!")
    app.run_polling()

if __name__ == "__main__":
    main()
