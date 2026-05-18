#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v4.3 — Fixed Edition
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
# ✨ Custom Emoji
# ============================================

def get_emoji_prefix() -> str:
    return "📛❤️❤️👑💙💙🔥🌎😹😁"

async def send_premium_message(chat_id, text: str, context: ContextTypes.DEFAULT_TYPE,
                                reply_to_message_id=None, parse_mode=ParseMode.MARKDOWN):
    full_text = get_emoji_prefix() + "\n" + text
    try:
        return await context.bot.send_message(
            chat_id=chat_id,
            text=full_text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as e:
        logger.error(f"خطا در send_premium_message: {e}")
        return await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )

async def reply_premium(update: Update, text: str, context: ContextTypes.DEFAULT_TYPE,
                         reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    full_text = get_emoji_prefix() + "\n" + text
    try:
        return await update.message.reply_text(
            full_text,
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
            greeting = "خوش اومدی عمو🙄"
        else:
            greeting = "خوش اومدی خاله 😂"

        text = f"👤 **{member.first_name}**\n🆔 `{member.id}`\n👋 {greeting}"
        try:
            await send_premium_message(chat_id, text, context)
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
        await send_premium_message(chat_id, text, context)
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
                    await send_premium_message(
                        chat_id,
                        f"🔇 [{update.effective_user.first_name}](tg://user?id={user_id}) بعد از ۲۰ اخطار سکوت شد! 🚫",
                        context,
                    )
                    warnings[key] = 0
                except Exception as e:
                    logger.error(f"خطا در سکوت: {e}")
            else:
                await send_premium_message(
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
                await send_premium_message(
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
            msg = await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=msg_id,
                disable_notification=True,
            )
            if msg.forward_from and msg.forward_from.id == target_user.id:
                await context.bot.delete_message(chat_id, msg_id)
                deleted += 1
            await context.bot.delete_message(chat_id, msg.message_id)
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
        await reply_premium(update, "❌ کاربر رو مشخص کن", context)
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون دلیل"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"🚫 **{user.first_name}** بن شد!\n📌 دلیل: {reason}", context)
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن", context)
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"✅ **{user.first_name}** آنبن شد!", context)
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن", context)
        return
    duration = parse_time(context.args[-1] if context.args else "")
    until = datetime.now() + duration if duration else None
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        t = f" برای {context.args[-1]}" if duration else " برای همیشه"
        await reply_premium(update, f"🔇 **{user.first_name}** میوت شد{t}!", context)
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن", context)
        return
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await reply_premium(update, f"🔊 **{user.first_name}** آنمیوت شد!", context)
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ کاربر رو مشخص کن", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await reply_premium(update, f"👢 **{user.first_name}** کیک شد!", context)
    except Exception as e:
        await reply_premium(update, f"❌ خطا: {e}", context)

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
        [InlineKeyboardButton("📋 دستورات", callback_data="menu_commands"),
         InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings")],
        [InlineKeyboardButton("📢 کانال ما", url=FORCE_SUB_CHANNEL)],
    ]
    await reply_premium(
        update,
        "🤖 **ربات مدیریت گروه یاشا**\n\nاز منو زیر استفاده کن:",
        context,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 **دستورات ربات:**\n\n"
        "👮 **مدیریت:**\n"
        "/ban — بن کردن کاربر\n"
        "/unban — آنبن کردن\n"
        "/mute — میوت کردن (مثال: /mute 1h)\n"
        "/unmute — آنمیوت کردن\n"
        "/kick — اخراج از گروه\n\n"
        "🔒 **قفل گروه:**\n"
        "/lock — قفل کردن گروه\n"
        "/unlock — باز کردن گروه\n\n"
        "🧹 **پاکسازی:**\n"
        "/purge — پاک کردن پیام‌های ۴۸ ساعت گذشته\n"
        "/purgeuser — پاک کردن پیام‌های یک کاربر خاص (با reply)\n\n"
        "⚙️ **تنظیمات:**\n"
        "/settings — پنل تنظیمات\n\n"
        "📢 **عضویت:**\n"
        "/join — بررسی عضویت در کانال\n\n"
        "⏱ زمان: s=ثانیه، m=دقیقه، h=ساعت، d=روز"
    )
    await reply_premium(update, text, context)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_commands":
        text = "📋 **دستورات:**\n/ban\n/unban\n/mute\n/unmute\n/kick\n/lock\n/unlock\n/purge\n/settings\n/join"
        buttons = [[InlineKeyboardButton("🔙 برگشت", callback_data="menu_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)
    elif query.data == "menu_settings":
        chat_id = query.message.chat_id
        await query.edit_message_reply_markup(reply_markup=build_settings_keyboard(chat_id))
    elif query.data == "menu_back":
        buttons = [
            [InlineKeyboardButton("📋 دستورات", callback_data="menu_commands"),
             InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings")],
            [InlineKeyboardButton("📢 کانال ما", url=FORCE_SUB_CHANNEL)],
        ]
        await query.edit_message_text(
            "🤖 **ربات مدیریت گروه یاشا**\n\nاز منو زیر استفاده کن:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
        )

# ============================================
# ⚙️ تنظیمات
# ============================================

def build_settings_keyboard(chat_id):
    def btn(label, key):
        val = get_setting(chat_id, key, 1)
        return InlineKeyboardButton(f"{'✅' if val else '❌'} {label}", callback_data=f"toggle_{key}")
    return InlineKeyboardMarkup([
        [btn("ولکام", "welcome_enabled"), btn("خداحافظی", "goodbye_enabled")],
        [btn("حذف لینک", "delete_links"), btn("آنتی اسپم", "delete_spam")],
        [btn("حذف استیکر", "delete_stickers")],
        [InlineKeyboardButton("❌ بستن", callback_data="close_settings")],
    ])

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    await reply_premium(
        update,
        "⚙️ **تنظیمات گروه**",
        context,
        reply_markup=build_settings_keyboard(update.effective_chat.id),
    )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
# 🚀 اجرای ربات
# ============================================

def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()

    # دستورات (فقط انگلیسی)
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
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

    # callback ها
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|close_settings)"))

    # پیام‌ها
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))

    logger.info("✅ ربات یاشا v4.3 شروع به کار کرد!")
    app.run_polling()

if __name__ == "__main__":
    main()
