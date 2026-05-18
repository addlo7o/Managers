#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v5.0 — Persian Edition
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
# Emojis
# ============================================

CUSTOM_EMOJIS = {
    "heart_blue": {"id": "5377688663960331522", "char": "💙", "length": 2},
    "heart_red": {"id": "5370897968478047651", "char": "❤️", "length": 2},
    "earth": {"id": "5377357058125340868", "char": "🌎", "length": 2},
    "grin": {"id": "5233605022419270727", "char": "😁", "length": 2},
    "cool": {"id": "5114163768623895481", "char": "🆒", "length": 2},
    "check": {"id": "5208880351690112495", "char": "✅", "length": 1},
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
    except Exception as e:
        return await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)

# ============================================
# Python Code Explanations
# ============================================

COMMAND_EXPLANATIONS = {
    "lock": {
        "title": "قفل گروه",
        "code": 'class GroupLock:\n    def execute(chat_id):\n        permissions = ChatPermissions(can_send_messages=False)\n        bot.set_chat_permissions(chat_id, permissions)\n        return "Group locked"',
        "benefit": "🛡️ جلوگیری از هرج و مرج"
    },
    "unlock": {
        "title": "باز کردن گروه",
        "code": 'class GroupUnlock:\n    def execute(chat_id):\n        permissions = ChatPermissions(can_send_messages=True)\n        bot.set_chat_permissions(chat_id, permissions)\n        return "Group unlocked"',
        "benefit": "🎉 بازگشت به حالت عادی"
    },
    "ban": {
        "title": "بن کردن کاربر",
        "code": 'class UserBan:\n    def execute(chat_id, user_id):\n        bot.ban_chat_member(chat_id, user_id)\n        return f"User {user_id} banned"',
        "benefit": "⚠️ حذف کاربران مخرب"
    },
    "unban": {
        "title": "آنبن کردن کاربر",
        "code": 'class UserUnban:\n    def execute(chat_id, user_id):\n        bot.unban_chat_member(chat_id, user_id)\n        return f"User {user_id} unbanned"',
        "benefit": "🔄 فرصت دوباره"
    },
    "mute": {
        "title": "میوت کاربر",
        "code": 'class UserMute:\n    def execute(chat_id, user_id, duration=None):\n        permissions = ChatPermissions(can_send_messages=False)\n        if duration:\n            bot.restrict_chat_member(chat_id, user_id, permissions, until_date=datetime.now()+duration)\n        else:\n            bot.restrict_chat_member(chat_id, user_id, permissions)\n        return f"User {user_id} muted"',
        "benefit": "⏰ تنبیه موقت"
    },
    "unmute": {
        "title": "آنمیوت کاربر",
        "code": 'class UserUnmute:\n    def execute(chat_id, user_id):\n        permissions = ChatPermissions(can_send_messages=True)\n        bot.restrict_chat_member(chat_id, user_id, permissions)\n        return f"User {user_id} unmuted"',
        "benefit": "🗣️ بازگشت به گفتگو"
    },
    "kick": {
        "title": "کیک کاربر",
        "code": 'class UserKick:\n    def execute(chat_id, user_id):\n        bot.ban_chat_member(chat_id, user_id)\n        bot.unban_chat_member(chat_id, user_id)\n        return f"User {user_id} kicked"',
        "benefit": "🚪 اخطار جدی"
    },
    "purge": {
        "title": "پاکسازی پیام‌ها",
        "code": 'class MessagePurge:\n    def execute(chat_id, count=300):\n        deleted = 0\n        for msg_id in range(current, current-count, -1):\n            try:\n                bot.delete_message(chat_id, msg_id)\n                deleted += 1\n            except:\n                pass\n        return f"{deleted} messages deleted"',
        "benefit": "🧽 نظافت گروه"
    },
}

async def send_python_explanation(update, context, command):
    if command not in COMMAND_EXPLANATIONS:
        return
    info = COMMAND_EXPLANATIONS[command]
    text = "📚 توضیحات فنی دستور: " + info["title"] + "\n\n━━━━━━━━━━━━━━━━━━━━━━\n📝 کد پایتون:\n```python\n" + info["code"] + "\n```\n\n━━━━━━━━━━━━━━━━━━━━━━\n" + info["benefit"] + "\n\n💡 این کد عملکرد داخلی ربات است"
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
# Anti Bad Words
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

# ============================================
# Anti Spam
# ============================================

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
    if get_setting(chat_id, "delete_stickers", 0) and update.message.sticker:
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

# ============================================
# Commands (English names for handler, Persian for users)
# ============================================

async def lock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=False))
        await reply_premium(update, "🔒 گروه قفل شد! فقط ادمین‌ها می‌تونن پیام بدن.", context)
        await send_python_explanation(update, context, "lock")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unlock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True))
        await reply_premium(update, "🔓 گروه باز شد! همه می‌تونن پیام بدن.", context)
        await send_python_explanation(update, context, "unlock")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def ban_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target = await context.bot.get_chat(int(context.args[0]))
        except:
            pass
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن یا ID بده", context)
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون دلیل"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await reply_premium(update, f"🚫 **{target.first_name}** بن شد!\n📌 دلیل: {reason}", context)
        await send_python_explanation(update, context, "ban")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unban_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target = await context.bot.get_chat(int(context.args[0]))
        except:
            pass
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن یا ID بده", context)
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await reply_premium(update, f"✅ **{target.first_name}** آنبن شد!", context)
        await send_python_explanation(update, context, "unban")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def mute_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target = await context.bot.get_chat(int(context.args[0]))
        except:
            pass
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن یا ID بده\nمثال: /mute 1h", context)
        return
    time_arg = None
    if context.args:
        if update.message.reply_to_message:
            time_arg = context.args[0] if context.args else None
        else:
            time_arg = context.args[1] if len(context.args) > 1 else None
    duration = None
    if time_arg:
        match = re.match(r"(\d+)([smhd])", time_arg)
        if match:
            v, u = int(match.group(1)), match.group(2)
            durations = {"s": timedelta(seconds=v), "m": timedelta(minutes=v), "h": timedelta(hours=v), "d": timedelta(days=v)}
            duration = durations.get(u)
    until = datetime.now() + duration if duration else None
    time_text = f" برای {time_arg}" if duration else " برای همیشه"
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
        await reply_premium(update, f"🔇 **{target.first_name}** میوت شد{time_text}!", context)
        await send_python_explanation(update, context, "mute")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unmute_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target = await context.bot.get_chat(int(context.args[0]))
        except:
            pass
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن یا ID بده", context)
        return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True))
        await reply_premium(update, f"🔊 **{target.first_name}** آنمیوت شد!", context)
        await send_python_explanation(update, context, "unmute")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def kick_cmd(update, context):
    if not await is_admin(update, context):
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target = await context.bot.get_chat(int(context.args[0]))
        except:
            pass
    if not target:
        await reply_premium(update, "❌ روی پیام کاربر reply کن یا ID بده", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await reply_premium(update, f"👢 **{target.first_name}** کیک شد!", context)
        await send_python_explanation(update, context, "kick")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def purge_cmd(update, context):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    chat_id = update.effective_chat.id
    current = update.message.message_id
    deleted = 0
    await reply_premium(update, "🧹 در حال پاکسازی پیام‌های ۴۸ ساعت گذشته...", context)
    for msg_id in range(current, max(current - 300, 1), -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except:
            pass
        await asyncio.sleep(0.05)
    await reply_premium(update, f"✅ پاکسازی تموم شد! {deleted} پیام حذف شد.", context)
    await send_python_explanation(update, context, "purge")

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
    await send_python_explanation(update, context, "settings") if "settings" in COMMAND_EXPLANATIONS else None

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

🔒 `/lock` یا `/قفل` - قفل کردن گروه
🔓 `/unlock` یا `/بازکن` - باز کردن گروه
🚫 `/ban` یا `/بن` - بن کردن کاربر
✅ `/unban` یا `/آنبن` - آنبن کردن کاربر
🔇 `/mute` یا `/میوت` - میوت کاربر
🔊 `/unmute` یا `/آنمیوت` - آنمیوت کاربر
👢 `/kick` یا `/کیک` - کیک کردن کاربر

━━━━━━━━━━━━━━━━━━━━━━
🧹 **دستورات پاکسازی**
━━━━━━━━━━━━━━━━━━━━━━

🗑 `/purge` یا `/پاکسازی` - پاک کردن پیام‌های اخیر
👤 `/purgeuser` یا `/پاکسازی_کاربر` - پاک کردن پیام‌های یک کاربر

━━━━━━━━━━━━━━━━━━━━━━
⚙️ **دستورات عمومی**
━━━━━━━━━━━━━━━━━━━━━━

🎯 `/start` - منوی اصلی
❓ `/help` - راهنما
⚙️ `/settings` یا `/تنظیمات` - تنظیمات گروه
📢 `/join` یا `/عضویت` - بررسی عضویت در کانال

━━━━━━━━━━━━━━━━━━━━━━
⏱ **نحوه استفاده از /mute یا /میوت**
━━━━━━━━━━━━━━━━━━━━━━

`/mute 30s` - 30 ثانیه
`/mute 5m` - 5 دقیقه
`/mute 2h` - 2 ساعت
`/mute 1d` - 1 روز
`/mute` - میوت دائمی

━━━━━━━━━━━━━━━━━━━━━━
💡 **نکات مهم**
━━━━━━━━━━━━━━━━━━━━━━

• برای بن، میوت، کیک روی پیام کاربر **reply** کنید
• بعد از هر دستور، کد پایتون آن نمایش داده می‌شود
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

    # English commands (primary)
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

    # Persian commands (alias using filters)
    app.add_handler(MessageHandler(filters.Regex(r'^/\u0642\u0641\u0644($| )'), lock_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u0628\u0627\u0632\u06A9\u0646($| )'), unlock_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u0628\u0646($| )'), ban_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u0622\u0646\u0628\u0646($| )'), unban_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u0645\u06CC\u0648\u062A($| )'), mute_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u0622\u0646\u0645\u06CC\u0648\u062A($| )'), unmute_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u06A9\u06CC\u06A9($| )'), kick_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u067E\u0627\u06A9\u0633\u0627\u0632\u06CC($| )'), purge_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u067E\u0627\u06A9\u0633\u0627\u0632\u06CC_\u06A9\u0627\u0631\u0628\u0631($| )'), purge_user_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u062A\u0646\u0638\u06CC\u0645\u0627\u062A($| )'), settings_cmd))
    app.add_handler(MessageHandler(filters.Regex(r'^/\u0639\u0636\u0648\u06CC\u062A($| )'), join_cmd))

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
