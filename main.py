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
        "code": "class GroupLock:\n    def execute(chat_id):\n        permissions = ChatPermissions(can_send_messages=False)\n        bot.set_chat_permissions(chat_id, permissions)\n        نتیجه: فقط ادمین‌ها می‌تونن پیام بدن",
        "benefit": "🛡️ فایده برای گروه: جلوگیری از هرج و مرج، کنترل کامل توسط ادمین‌ها"
    },
    "unlock": {
        "title": "🔓 باز کردن گروه",
        "code": "class GroupUnlock:\n    def execute(chat_id):\n        permissions = ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True)\n        bot.set_chat_permissions(chat_id, permissions)\n        نتیجه: همه اعضا می‌تونن پیام بدن",
        "benefit": "🎉 فایده برای گروه: بازگشت به حالت عادی، افزایش تعامل اعضا"
    },
    "ban": {
        "title": "🚫 بن کردن کاربر",
        "code": "class UserBan:\n    def execute(chat_id, user_id, reason):\n        bot.ban_chat_member(chat_id, user_id)\n        نتیجه: کاربر دیگه نمیتونه به گروه ملحق بشه",
        "benefit": "⚠️ فایده برای گروه: حذف کاربران مخرب، اسپمرها و مزاحمان"
    },
    "unban": {
        "title": "✅ آنبن کردن کاربر",
        "code": "class UserUnban:\n    def execute(chat_id, user_id):\n        bot.unban_chat_member(chat_id, user_id)\n        نتیجه: کاربر می‌تونه دوباره به گروه ملحق بشه",
        "benefit": "🔄 فایده برای گروه: فرصت دوباره به کاربرانی که اشتباه کردن"
    },
    "mute": {
        "title": "🔇 میوت کردن کاربر",
        "code": "class UserMute:\n    def execute(chat_id, user_id, duration=None):\n        permissions = ChatPermissions(can_send_messages=False)\n        if duration:\n            until_date = datetime.now() + duration\n            bot.restrict_chat_member(chat_id, user_id, permissions, until_date=until_date)\n        else:\n            bot.restrict_chat_member(chat_id, user_id, permissions)\n        نتیجه: کاربر می‌تونه گروه رو ببینه ولی نتونه پیام بفرسته",
        "benefit": "⏰ فایده برای گروه: تنبیه موقت بدون حذف کاربر، قابل تنظیم با زمان"
    },
    "unmute": {
        "title": "🔊 آنمیوت کردن کاربر",
        "code": "class UserUnmute:\n    def execute(chat_id, user_id):\n        permissions = ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)\n        bot.restrict_chat_member(chat_id, user_id, permissions)\n        نتیجه: کاربر می‌تونه دوباره پیام بفرسته",
        "benefit": "🗣️ فایده برای گروه: بازگشت کاربر به چرخه گفتگو"
    },
    "kick": {
        "title": "👢 کیک کردن کاربر",
        "code": "class UserKick:\n    def execute(chat_id, user_id):\n        bot.ban_chat_member(chat_id, user_id)\n        bot.unban_chat_member(chat_id, user_id)\n        نتیجه: کاربر از گروه خارج میشه ولی می‌تونه دوباره بیاد",
        "benefit": "🚪 فایده برای گروه: اخطار جدی بدون حذف دائمی"
    },
    "purge": {
        "title": "🧹 پاکسازی پیام‌ها",
        "code": "class MessagePurge:\n    def execute(chat_id, message_count=500):\n        deleted = 0\n        current_msg_id = get_current_message_id()\n        for msg_id in range(current_msg_id, current_msg_id - message_count, -1):\n            try:\n                bot.delete_message(chat_id, msg_id)\n                deleted += 1\n            except:\n                pass\n        نتیجه: پیام‌های غیرضروری پاک میشن",
        "benefit": "🧽 فایده برای گروه: نظافت گروه، حذف اسپم و پیام‌های تکراری"
    },
    "settings": {
        "title": "⚙️ تنظیمات گروه",
        "code": "class GroupSettings:\n    settings = {\n        'welcome_enabled': 'فعال/غیرفعال کردن پیام خوش‌آمدگویی',\n        'delete_links': 'حذف خودکار لینک‌ها',\n        'delete_spam': 'فیلتر کلمات اسپم',\n        'delete_stickers': 'حذف استیکرها'\n    }\n    def toggle_setting(key):\n        current = get_setting(chat_id, key)\n        set_setting(chat_id, key, not current)\n        نتیجه: تنظیمات مطابق نیاز گروه تغییر می‌کنه",
        "benefit": "🎛️ فایده برای گروه: شخصی‌سازی رفتار ربات بر اساس نیاز گروه"
    }
}

async def send_command_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    if command not in COMMAND_EXPLANATIONS:
        return
    
    info = COMMAND_EXPLANATIONS[command]
    
    text = "📚 توضیحات فنی دستور: " + info['title'] + "\n\n━━━━━━━━━━━━━━━━━━━━━━\n📝 کد پایتون:\n```\n" + info['code'] + "\n```\n\n━━━━━━━━━━━━━━━━━━━━━━\n" + info['benefit'] + "\n\n💡 این توضیحات نشان‌دهنده عملکرد داخلی ربات است."
    
    await reply_premium(update, text, context)

# ============================================
# 📌 عضویت اجباری
# ============================================

async def is_force_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for ch_id in FORCE_SUB_IDS:
        if ch_id == 0:
            continue
        try:
            member = await context.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                return False
        except Exception:
            return False
    return True

async def force_sub_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await is_force_subscribed(user.id, context):
        await reply_premium(update, "✅ عضویت تأیید شد! به گروه خوش اومدی 🎉", context)
        return
    buttons = [
        [InlineKeyboardButton(f"📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_sub")],
    ]
    await reply_premium(
        update,
        f"🔒 برای استفاده از ربات باید عضو کانال {FORCE_SUB_USERNAME} بشی:",
        context,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if await is_force_subscribed(user.id, context):
        await query.edit_message_text("✅ عضویت تأیید شد! حالا می‌تونی بفرستی 🎉")
    else:
        await query.answer("❌ هنوز عضو نشدی!", show_alert=True)

# ============================================
# 👋 خوش‌آمدگویی
# ============================================

welcome_counter = {}

async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        if welcome_counter[chat_id] % 2 == 1:
            greeting = "خوش اومدی عمو 🙄"
        else:
            greeting = "خوش اومدی خاله 😂"

        text = f"👤 **{member.first_name}**\n🆔 `{member.id}`\n👋 {greeting}"
        try:
            await send_premium(chat_id, text, context)
        except Exception as e:
            logger.error(f"خطا در ولکام: {e}")

async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await send_premium(chat_id, text, context)
    except Exception as e:
        logger.error(f"خطا در خداحافظی: {e}")

# ============================================
# 🤬 آنتی بدزبانی
# ============================================

async def anti_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.lower()

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except Exception:
        pass

    for word in BAD_WORDS:
        if word.lower() in text:
            key = (chat_id, user_id)
            warnings[key] = warnings.get(key, 0) + 1
            count = warnings[key]

            if count >= 20:
                try:
                    await context.bot.restrict_chat_member(
                        chat_id, user_id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=datetime.now() + timedelta(hours=24),
                    )
                    await send_premium(
                        chat_id,
                        f"🔇 [{update.effective_user.first_name}](tg://user?id={user_id}) بعد از ۲۰ اخطار سکوت شد! 🚫",
                        context,
                    )
                    warnings[key] = 0
                except Exception as e:
                    logger.error(f"خطا در سکوت: {e}")
            else:
                await send_premium(
                    chat_id,
                    f"⚠️ [{update.effective_user.first_name}](tg://user?id={user_id}) مراقب زبونت باش!\n🔴 اخطار: {count}/20",
                    context,
                )
            await update.message.delete()
            return

# ============================================
# 🚫 آنتی اسپم
# ============================================

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.lower()

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except Exception:
        pass

    if get_setting(chat_id, "delete_links", 1):
        for domain in FORBIDDEN_DOMAINS:
            if domain in text:
                await update.message.delete()
                await send_premium(
                    chat_id,
                    f"⚠️ [{update.effective_user.first_name}](tg://user?id={user_id}) لینک ممنوع ارسال کرد!",
                    context,
                )
                return

    if get_setting(chat_id, "delete_spam", 1):
        for word in SPAM_KEYWORDS:
            if word in text:
                await update.message.delete()
                return

    if get_setting(chat_id, "delete_stickers", 0) and update.message.sticker:
        await update.message.delete()
        return

    await anti_bad_words(update, context)

# ============================================
# 🔒 قفل و باز کردن گروه
# ============================================

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id in SUDO_USERS:
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(
            update.effective_chat.id,
            ChatPermissions(can_send_messages=False),
        )
        await reply_premium(update, "🔒 گروه قفل شد! فقط ادمین‌ها می‌تونن پیام بدن.", context)
        await send_command_explanation(update, context, "lock")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(
            update.effective_chat.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
            ),
        )
        await reply_premium(update, "🔓 گروه باز شد! همه می‌تونن پیام بدن.", context)
        await send_command_explanation(update, context, "unlock")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

# ============================================
# 🧹 پاکسازی پیام‌ها
# ============================================

async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return

    chat_id = update.effective_chat.id
    current_msg_id = update.message.message_id
    deleted = 0

    await reply_premium(update, "🧹 در حال پاکسازی پیام‌های ۴۸ ساعت گذشته...", context)

    for msg_id in range(current_msg_id, max(current_msg_id - 500, 1), -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except Exception:
            pass
        await asyncio.sleep(0.1)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ پاکسازی تموم شد!\n🗑 {deleted} پیام حذف شد.",
        )
        await send_command_explanation(update, context, "purge")
    except Exception as e:
        logger.error(f"خطا در purge: {e}")

async def purge_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها!", context)
        return

    if not update.message.reply_to_message:
        await reply_premium(update, "❌ روی پیام کاربر reply کن", context)
        return

    target_user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    current_msg_id = update.message.message_id
    deleted = 0

    for msg_id in range(current_msg_id, max(current_msg_id - 200, 1), -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except Exception:
            pass
        await asyncio.sleep(0.1)

    await reply_premium(update, f"✅ {deleted} پیام از {target_user.first_name} حذف شد.", context)

# ============================================
# 🔨 دستورات ادمین
# ============================================

async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    if context.args:
        try:
            return await context.bot.get_chat(int(context.args[0]))
        except Exception:
            return None
    return None

def parse_time(text: str):
    m = re.match(r"(\d+)([smhd])", text or "")
    if not m:
        return None
    v, u = int(m.group(1)), m.group(2)
    return {"s": timedelta(seconds=v), "m": timedelta(minutes=v),
            "h": timedelta(hours=v), "d": timedelta(days=v)}.get(u)

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن (reply یا ID)", context)
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون دلیل"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"🚫 **{user.first_name}** بن شد!\n📌 دلیل: {reason}", context)
        await send_command_explanation(update, context, "ban")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن (reply یا ID)", context)
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"✅ **{user.first_name}** آنبن شد!", context)
        await send_command_explanation(update, context, "unban")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن (reply یا ID)\nمثال: /mute 1h", context)
        return
    
    time_arg = None
    if context.args and len(context.args) > 0:
        time_arg = context.args[0]
    
    duration = parse_time(time_arg)
    until = datetime.now() + duration if duration else None
    time_text = f" برای {time_arg}" if duration else " برای همیشه"
    
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await reply_premium(update, f"🔇 **{user.first_name}** میوت شد{time_text}!", context)
        await send_command_explanation(update, context, "mute")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن (reply یا ID)", context)
        return
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
            ),
        )
        await reply_premium(update, f"🔊 **{user.first_name}** آنمیوت شد!", context)
        await send_command_explanation(update, context, "unmute")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن (reply یا ID)", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"👢 **{user.first_name}** کیک شد!", context)
        await send_command_explanation(update, context, "kick")
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

# ============================================
# 📋 منوی کامل دستورات
# ============================================

def get_commands_menu() -> str:
    return """
📋 منوی کامل دستورات ربات یاشا

━━━━━━━━━━━━━━━━━━━━━━
👮 دستورات مدیریتی
━━━━━━━━━━━━━━━━━━━━━━

🔨 /ban - بن کردن کاربر
🔓 /unban - آنبن کردن کاربر
🔇 /mute - میوت (سکوت) کاربر
🔊 /unmute - آنمیوت کاربر
👢 /kick - اخراج کاربر از گروه
🔒 /lock - قفل کردن گروه
🔓 /unlock - باز کردن گروه

━━━━━━━━━━━━━━━━━━━━━━
🧹 دستورات پاکسازی
━━━━━━━━━━━━━━━━━━━━━━

🗑 /purge - پاک کردن پیام‌های ۴۸ ساعت اخیر
👤 /purgeuser - پاک کردن پیام‌های یک کاربر خاص

━━━━━━━━━━━━━━━━━━━━━━
⚙️ دستورات عمومی
━━━━━━━━━━━━━━━━━━━━━━

🎯 /start - منوی اصلی ربات
❓ /help - نمایش راهنما
⚙️ /settings - پنل تنظیمات گروه
📢 /join - بررسی عضویت در کانال
📚 /about - توضیحات کامل ربات و قابلیت‌ها

━━━━━━━━━━━━━━━━━━━━━━
⏱ نحوه استفاده از زمان در /mute
━━━━━━━━━━━━━━━━━━━━━━

/mute 30s - 30 ثانیه
/mute 5m - 5 دقیقه
/mute 2h - 2 ساعت
/mute 1d - 1 روز
/mute - میوت دائمی

━━━━━━━━━━━━━━━━━━━━━━
💡 نکات مهم
━━━━━━━━━━━━━━━━━━━━━━

• برای ban, unban, mute, kick روی پیام کاربر reply کنید
• یا می‌توانید ID عددی کاربر را وارد کنید
• دستورات purgeuser نیز نیاز به reply دارد
• تنظیمات گروه با /settings قابل تغییر است
• بعد از هر دستور مدیریتی، توضیحات فنی آن به صورت کد پایتون نمایش داده می‌شود
"""

# ============================================
# ℹ️ منو و راهنما
# ============================================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_force_subscribed(update.effective_user.id, context):
        buttons = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)],
            [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_sub")],
        ]
        await reply_premium(
            update,
            f"🔒 برای استفاده از ربات باید عضو کانال {FORCE_SUB_USERNAME} بشی!",
            context,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    buttons = [
        [InlineKeyboardButton("📋 مشاهده دستورات", callback_data="menu_commands")],
        [InlineKeyboardButton("⚙️ تنظیمات گروه", callback_data="menu_settings")],
        [InlineKeyboardButton("📚 درباره ربات", callback_data="menu_about")],
        [InlineKeyboardButton("📢 کانال ما", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("❌ بستن", callback_data="close_menu")],
    ]
    await reply_premium(
        update,
        "🤖 ربات مدیریت گروه یاشا\n\nاز منوی زیر می‌توانید دستورات و تنظیمات را مشاهده کنید:",
        context,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_premium(update, get_commands_menu(), context)

async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📚 ربات مدیریت گروه یاشا (Yasha Group Bot)\n\n━━━━━━━━━━━━━━━━━━━━━━\n🤖 ربات مدیریت گروه چیست؟\n━━━━━━━━━━━━━━━━━━━━━━\n\nربات مدیریت گروه یک ابزار خودکار برای کنترل، نظارت و سازماندهی گروه‌های تلگرامی است.\n\n━━━━━━━━━━━━━━━━━━━━━━\n⚡ قابلیت‌های اصلی:\n━━━━━━━━━━━━━━━━━━━━━━\n\n🔒 قفل/باز کردن گروه\n🚫 مدیریت کاربران (بن، میوت، ک
