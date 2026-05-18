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
        logger.error(f"Error in send_premium: {e}")
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
        logger.error(f"Error in reply_premium: {e}")
        return await update.message.reply_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

# ============================================
# 📚 توضیحات فنی دستورات
# ============================================

COMMAND_EXPLANATIONS = {
    "lock": {
        "title": "Lock Group",
        "code": "class GroupLock:\n    def execute(chat_id):\n        permissions = ChatPermissions(can_send_messages=False)\n        bot.set_chat_permissions(chat_id, permissions)",
        "benefit": "Benefit: Prevent chaos, full admin control"
    },
    "unlock": {
        "title": "Unlock Group",
        "code": "class GroupUnlock:\n    def execute(chat_id):\n        permissions = ChatPermissions(can_send_messages=True)\n        bot.set_chat_permissions(chat_id, permissions)",
        "benefit": "Benefit: Return to normal, increase member interaction"
    },
    "ban": {
        "title": "Ban User",
        "code": "class UserBan:\n    def execute(chat_id, user_id):\n        bot.ban_chat_member(chat_id, user_id)",
        "benefit": "Benefit: Remove spam and harmful users"
    },
    "unban": {
        "title": "Unban User",
        "code": "class UserUnban:\n    def execute(chat_id, user_id):\n        bot.unban_chat_member(chat_id, user_id)",
        "benefit": "Benefit: Second chance for users"
    },
    "mute": {
        "title": "Mute User",
        "code": "class UserMute:\n    def execute(chat_id, user_id):\n        permissions = ChatPermissions(can_send_messages=False)\n        bot.restrict_chat_member(chat_id, user_id, permissions)",
        "benefit": "Benefit: Temporary punishment without removal"
    },
    "unmute": {
        "title": "Unmute User",
        "code": "class UserUnmute:\n    def execute(chat_id, user_id):\n        permissions = ChatPermissions(can_send_messages=True)\n        bot.restrict_chat_member(chat_id, user_id, permissions)",
        "benefit": "Benefit: Restore user to conversation"
    },
    "kick": {
        "title": "Kick User",
        "code": "class UserKick:\n    def execute(chat_id, user_id):\n        bot.ban_chat_member(chat_id, user_id)\n        bot.unban_chat_member(chat_id, user_id)",
        "benefit": "Benefit: Serious warning without permanent removal"
    },
    "purge": {
        "title": "Purge Messages",
        "code": "class MessagePurge:\n    def execute(chat_id):\n        for msg_id in range(current, current-500, -1):\n            bot.delete_message(chat_id, msg_id)",
        "benefit": "Benefit: Clean group, remove spam messages"
    },
    "settings": {
        "title": "Group Settings",
        "code": "class GroupSettings:\n    def toggle_setting(key):\n        current = get_setting(key)\n        set_setting(key, not current)",
        "benefit": "Benefit: Customize bot behavior for your group"
    }
}

async def send_command_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    if command not in COMMAND_EXPLANATIONS:
        return
    
    info = COMMAND_EXPLANATIONS[command]
    
    text = f"📚 Command Explanation: {info['title']}\n\n━━━━━━━━━━━━━━━━━━━━━━\n📝 Python Code:\n```\n{info['code']}\n```\n\n━━━━━━━━━━━━━━━━━━━━━━\n{info['benefit']}"
    
    await reply_premium(update, text, context)

# ============================================
# 📌 Force Subscription
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
        await reply_premium(update, "✅ Membership confirmed! Welcome to the group", context)
        return
    buttons = [
        [InlineKeyboardButton("📢 Join Channel", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("🔄 Check Membership", callback_data="check_sub")],
    ]
    await reply_premium(
        update,
        f"🔒 You must join {FORCE_SUB_USERNAME} to use this bot:",
        context,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if await is_force_subscribed(user.id, context):
        await query.edit_message_text("✅ Membership confirmed! You can now send messages")
    else:
        await query.answer("❌ You are not a member yet!", show_alert=True)

# ============================================
# 👋 Welcome & Goodbye
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
            greeting = "Welcome!"
        else:
            greeting = "Welcome!"

        text = f"👤 {member.first_name}\n🆔 {member.id}\n👋 {greeting}"
        try:
            await send_premium(chat_id, text, context)
        except Exception as e:
            logger.error(f"Welcome error: {e}")

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
        logger.error(f"Goodbye error: {e}")

# ============================================
# 🤬 Anti Bad Words
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
                        f"🔇 {update.effective_user.first_name} has been muted after 20 warnings",
                        context,
                    )
                    warnings[key] = 0
                except Exception as e:
                    logger.error(f"Mute error: {e}")
            else:
                await send_premium(
                    chat_id,
                    f"⚠️ {update.effective_user.first_name} warning: {count}/20",
                    context,
                )
            await update.message.delete()
            return

# ============================================
# 🚫 Anti Spam
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
                    f"⚠️ {update.effective_user.first_name} sent a forbidden link",
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
# 🔒 Lock & Unlock
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
        await reply_premium(update, "❌ Only admins!", context)
        return
    try:
        await context.bot.set_chat_permissions(
            update.effective_chat.id,
            ChatPermissions(can_send_messages=False),
        )
        await reply_premium(update, "🔒 Group locked! Only admins can send messages.", context)
        await send_command_explanation(update, context, "lock")
    except Exception as e:
        await reply_premium(update, f"❌ Error: {e}", context)

async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ Only admins!", context)
        return
    try:
        await context.bot.set_chat_permissions(
            update.effective_chat.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
            ),
        )
        await reply_premium(update, "🔓 Group unlocked! Everyone can send messages.", context)
        await send_command_explanation(update, context, "unlock")
    except Exception as e:
        await reply_premium(update, f"❌ Error: {e}", context)

# ============================================
# 🧹 Purge Commands
# ============================================

async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ Only admins!", context)
        return

    chat_id = update.effective_chat.id
    current_msg_id = update.message.message_id
    deleted = 0

    await reply_premium(update, "🧹 Cleaning messages from last 48 hours...", context)

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
            text=f"✅ Cleanup complete! {deleted} messages deleted.",
        )
        await send_command_explanation(update, context, "purge")
    except Exception as e:
        logger.error(f"Purge error: {e}")

async def purge_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ Only admins!", context)
        return

    if not update.message.reply_to_message:
        await reply_premium(update, "❌ Reply to a user's message", context)
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

    await reply_premium(update, f"✅ {deleted} messages from {target_user.first_name} deleted.", context)

# ============================================
# 🔨 Admin Commands
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
        await reply_premium(update, "❌ Specify user (reply or ID)", context)
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"🚫 {user.first_name} banned!\nReason: {reason}", context)
        await send_command_explanation(update, context, "ban")
    except Exception as e:
        await reply_premium(update, f"❌ Error: {e}", context)

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ Specify user (reply or ID)", context)
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"✅ {user.first_name} unbanned!", context)
        await send_command_explanation(update, context, "unban")
    except Exception as e:
        await reply_premium(update, f"❌ Error: {e}", context)

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ Specify user (reply or ID)\nExample: /mute 1h", context)
        return
    
    time_arg = None
    if context.args and len(context.args) > 0:
        time_arg = context.args[0]
    
    duration = parse_time(time_arg)
    until = datetime.now() + duration if duration else None
    time_text = f" for {time_arg}" if duration else " permanently"
    
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await reply_premium(update, f"🔇 {user.first_name} muted{time_text}!", context)
        await send_command_explanation(update, context, "mute")
    except Exception as e:
        await reply_premium(update, f"❌ Error: {e}", context)

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ Specify user (reply or ID)", context)
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
        await reply_premium(update, f"🔊 {user.first_name} unmuted!", context)
        await send_command_explanation(update, context, "unmute")
    except Exception as e:
        await reply_premium(update, f"❌ Error: {e}", context)

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ Specify user (reply or ID)", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"👢 {user.first_name} kicked!", context)
        await send_command_explanation(update, context, "kick")
    except Exception as e:
        await reply_premium(update, f"❌ Error: {e}", context)

# ============================================
# 📋 Menu & Help
# ============================================

def get_commands_menu() -> str:
    return """
📋 Yasha Bot Commands Menu

━━━━━━━━━━━━━━━━━━━━━━
👮 Admin Commands
━━━━━━━━━━━━━━━━━━━━━━

/ban - Ban user
/unban - Unban user
/mute - Mute user
/unmute - Unmute user
/kick - Kick user
/lock - Lock group
/unlock - Unlock group

━━━━━━━━━━━━━━━━━━━━━━
🧹 Cleanup Commands
━━━━━━━━━━━━━━━━━━━━━━

/purge - Delete recent messages
/purgeuser - Delete specific user's messages

━━━━━━━━━━━━━━━━━━━━━━
⚙️ General Commands
━━━━━━━━━━━━━━━━━━━━━━

/start - Main menu
/help - Show help
/settings - Group settings
/join - Check channel membership
/about - About this bot

━━━━━━━━━━━━━━━━━━━━━━
⏱ Mute Time Examples
━━━━━━━━━━━━━━━━━━━━━━

/mute 30s - 30 seconds
/mute 5m - 5 minutes
/mute 2h - 2 hours
/mute 1d - 1 day
/mute - Permanent mute

━━━━━━━━━━━━━━━━━━━━━━
💡 Tips
━━━━━━━━━━━━━━━━━━━━━━

• Reply to a user's message for ban, mute, kick
• Or use their numeric ID
• /purgeuser also requires reply
• /settings to customize bot behavior
"""

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_force_subscribed(update.effective_user.id, context):
        buttons = [
            [InlineKeyboardButton("📢 Join Channel", url=FORCE_SUB_CHANNEL)],
            [InlineKeyboardButton("🔄 Check Membership", callback_data="check_sub")],
        ]
        await reply_premium(
            update,
            f"🔒 You must join {FORCE_SUB_USERNAME} to use this bot!",
            context,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    buttons = [
        [InlineKeyboardButton("📋 Commands", callback_data="menu_commands")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
        [InlineKeyboardButton("📚 About", callback_data="menu_about")],
        [InlineKeyboardButton("📢 Our Channel", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
    ]
    await reply_premium(
        update,
        "🤖 Yasha Group Bot\n\nUse the menu below:",
        context,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_premium(update, get_commands_menu(), context)

async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📚 Yasha Group Bot\n\nA powerful group management bot for Telegram.\n\nFeatures:\n- Group lock/unlock\n- User ban/mute/kick\n- Message purging\n- Anti-spam\n- Bad word filter\n- Welcome/goodbye messages\n- Force channel subscription\n\nAfter each admin command, Python code explanation is shown."
    
    await reply_premium(update, text, context)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_commands":
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
        await query.edit_message_text(
            get_commands_menu(),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif query.data == "menu_settings":
        chat_id = query.message.chat_id
        await query.edit_message_text(
            "⚙️ Group Settings\n\nSelect an option:",
            reply_markup=build_settings_keyboard(chat_id),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif query.data == "menu_about":
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
        text = "📚 Yasha Group Bot\n\nA powerful group management bot for Telegram.\n\nFeatures:\n- Group lock/unlock\n- User ban/mute/kick\n- Message purging\n- Anti-spam\n- Bad word filter\n- Welcome/goodbye messages\n- Force channel subscription"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif query.data == "menu_back":
        buttons = [
            [InlineKeyboardButton("📋 Commands", callback_data="menu_commands")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
            [InlineKeyboardButton("📚 About", callback_data="menu_about")],
            [InlineKeyboardButton("📢 Our Channel", url=FORCE_SUB_CHANNEL)],
            [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
        ]
        await query.edit_message_text(
            "🤖 Yasha Group Bot\n\nUse the menu below:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif query.data == "close_menu":
        await query.message.delete()

# ============================================
# ⚙️ Settings
# ============================================

def build_settings_keyboard(chat_id):
    def btn(label, key):
        val = get_setting(chat_id, key, 1)
        return InlineKeyboardButton(f"{'✅' if val else '❌'} {label}", callback_data=f"toggle_{key}")
    
    buttons = [
        [btn("Welcome Message", "welcome_enabled")],
        [btn("Goodbye Message", "goodbye_enabled")],
        [btn("Delete Links", "delete_links")],
        [btn("Anti Spam", "delete_spam")],
        [btn("Delete Stickers", "delete_stickers")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")],
        [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
    ]
    return InlineKeyboardMarkup(buttons)

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_premium(update, "❌ Only admins can change settings!", context)
        return
    await reply_premium(
        update,
        "⚙️ Group Settings Panel\n\nTap an option to toggle:",
        context,
        reply_markup=build_settings_keyboard(update.effective_chat.id),
    )
    await send_command_explanation(update, context, "settings")

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    if query.data == "close_menu":
        await query.message.delete()
        return
    if query.data == "menu_back":
        buttons = [
            [InlineKeyboardButton("📋 Commands", callback_data="menu_commands")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
            [InlineKeyboardButton("📚 About", callback_data="menu_about")],
            [InlineKeyboardButton("📢 Our Channel", url=FORCE_SUB_CHANNEL)],
            [InlineKeyboardButton("❌ Close", callback_data="close_menu")],
        ]
        await query.edit_message_text(
            "🤖 Yasha Group Bot\n\nUse the menu below:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    if query.data.startswith("toggle_"):
        key = query.data.replace("toggle_", "")
        current = get_setting(chat_id, key, 1)
        set_setting(chat_id, key, 0 if current else 1)
        
        status = "Enabled" if not current else "Disabled"
        await query.answer(f"Setting saved! {status}")
        await query.edit_message_reply_markup(reply_markup=build_settings_keyboard(chat_id))

# ============================================
# 🚀 Main
# ============================================

async def set_bot_commands(app: Application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help"),
        BotCommand("about", "About this bot"),
        BotCommand("settings", "Group settings"),
        BotCommand("join", "Check channel membership"),
        BotCommand("ban", "Ban user"),
        BotCommand("unban", "Unban user"),
        BotCommand("mute", "Mute user"),
        BotCommand("unmute", "Unmute user"),
        BotCommand("kick", "Kick user"),
        BotCommand("lock", "Lock group"),
        BotCommand("unlock", "Unlock group"),
        BotCommand("purge", "Delete recent messages"),
        BotCommand("purgeuser", "Delete user's messages"),
    ]
    await app.bot.set_my_commands(commands)

def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.post_init = set_bot_commands

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("join", force_sub_panel))
    app.add_handler(CommandHandler("purge", purge_cmd))
    app.add_handler(CommandHandler("purgeuser", purge_user_cmd))

    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^(menu_|close_menu)"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|menu_back|close_menu)"))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))

    logger.info("Yasha Bot v5.0 started successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
