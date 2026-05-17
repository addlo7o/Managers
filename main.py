#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v4.0 — Power Edition
# ============================================

import asyncio
import logging
import re
from datetime import datetime, timedelta

import config
from database import init_db, get_db, get_setting, set_setting

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, BotCommand
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

# ===== لیست سیاه =====
SPAM_KEYWORDS = ["join", "fast", "سایت", "🔞", "💰", "کلیک", "عضویت"]
FORBIDDEN_DOMAINS = ["bit.ly", "tinyurl.com", "t.me/+"]

BAD_WORDS = [
    "احمق", "خر", "گاو", "کودن", "نادان", "بی‌شعور", "بیشعور",
    "ابله", "حیوان", "مادرجنده", "کصکش", "کیر", "کون", "جنده",
    "اوبی", "عوضی", "بی‌ناموس", "بیناموس", "الاغ", "خفه",
    "idiot", "stupid", "fool", "dumb", "asshole", "bastard"
]

# ذخیره اخطارها در حافظه
warnings = {}

FORCE_SUB_CHANNEL = "https://t.me/dontworry80"
FORCE_SUB_USERNAME = "@dontworry80"

# ============================================
# 📌 عضویت اجباری
# ============================================

async def is_force_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not config.FORCE_SUB_CHANNELS:
        return True
    for ch, ch_id in zip(config.FORCE_SUB_CHANNELS, config.FORCE_SUB_IDS):
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
        await update.message.reply_text("✅ عضویت تأیید شد! به گروه خوش اومدی 🎉")
        return
    buttons = [
        [InlineKeyboardButton(f"📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_sub")],
    ]
    await update.message.reply_text(
        f"🔒 برای استفاده از ربات باید عضو کانال {FORCE_SUB_USERNAME} بشی:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
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
        mention = f"[{member.first_name}](tg://user?id={member.id})"

        welcome_counter[chat_id] += 1
        if welcome_counter[chat_id] % 2 == 1:
            greeting = "خوش اومدی عمو🙄"
        else:
            greeting = "خوش اومدی خاله 😂"

        text = (
            f"👤 **{member.first_name}**\n"
            f"🆔 `{member.id}`\n"
            f"👋 {greeting}"
        )
        try:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
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
    text = get_setting(chat_id, "goodbye_text") or config.GOODBYE_DEFAULT
    text = text.replace("{mention}", mention)
    try:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
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
                    await update.message.reply_text(
                        f"🔇 [{update.effective_user.first_name}](tg://user?id={user_id}) بعد از ۲۰ اخطار سکوت شد! 🚫",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    warnings[key] = 0
                except Exception as e:
                    logger.error(f"خطا در سکوت: {e}")
            else:
                await update.message.reply_text(
                    f"⚠️ [{update.effective_user.first_name}](tg://user?id={user_id}) مراقب زبونت باش!\n"
                    f"🔴 اخطار: {count}/20",
                    parse_mode=ParseMode.MARKDOWN,
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
                await update.message.reply_text(
                    f"⚠️ [{update.effective_user.first_name}](tg://user?id={user_id}) لینک ممنوع ارسال کرد!",
                    parse_mode=ParseMode.MARKDOWN,
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

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    try:
        await context.bot.set_chat_permissions(
            update.effective_chat.id,
            ChatPermissions(can_send_messages=False),
        )
        await update.message.reply_text("🔒 گروه قفل شد! فقط ادمین‌ها می‌تونن پیام بدن.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")


async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    try:
        await context.bot.set_chat_permissions(
            update.effective_chat.id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update.message.reply_text("🔓 گروه باز شد! همه می‌تونن پیام بدن.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")


# ============================================
# 🔨 دستورات ادمین
# ============================================

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id in config.SUDO_USERS:
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False


async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    if context.args:
        try:
            return await context.bot.get_chat(int(context.args[0]))
        except Exception:
            try:
                return await context.bot.get_chat(context.args[0])
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
        await update.message.reply_text("❌ کاربر رو مشخص کن")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "بدون دلیل"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"🚫 **{user.first_name}** بن شد!\n📌 دلیل: {reason}", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await update.message.reply_text("❌ کاربر رو مشخص کن")
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"✅ **{user.first_name}** آنبن شد!", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")


async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await update.message.reply_text("❌ کاربر رو مشخص کن")
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
        await update.message.reply_text(f"🔇 **{user.first_name}** میوت شد{t}!", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")


async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await update.message.reply_text("❌ کاربر رو مشخص کن")
        return
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True
            ),
        )
        await update.message.reply_text(f"🔊 **{user.first_name}** آنمیوت شد!", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")


async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = await get_target(update, context)
    if not user:
        await update.message.reply_text("❌ کاربر رو مشخص کن")
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"👢 **{user.first_name}** کیک شد!", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")


# ============================================
# ℹ️ منو و راهنما
# ============================================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_force_subscribed(update.effective_user.id, context):
        buttons = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)],
            [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_sub")],
        ]
        await update.message.reply_text(
            f"🔒 برای استفاده از ربات باید عضو کانال {FORCE_SUB_USERNAME} بشی!",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    buttons = [
        [InlineKeyboardButton("📋 دستورات", callback_data="menu_commands"),
         InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings")],
        [InlineKeyboardButton("📢 کانال ما", url=FORCE_SUB_CHANNEL)],
    ]
    await update.message.reply_text(
        "🤖 **ربات مدیریت گروه یاشا**\n\n"
        "از منو زیر استفاده کن:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN,
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
        "/lock یا /قفل — قفل کردن گروه\n"
        "/unlock یا /بازکن — باز کردن گروه\n\n"
        "⚙️ **تنظیمات:**\n"
        "/settings — پنل تنظیمات\n\n"
        "📢 **عضویت:**\n"
        "/join — بررسی عضویت در کانال\n\n"
        "⏱ زمان: s=ثانیه، m=دقیقه، h=ساعت، d=روز"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_commands":
        text = (
            "📋 **دستورات ربات:**\n\n"
            "/ban — بن کردن\n"
            "/unban — آنبن کردن\n"
            "/mute — میوت (مثال: /mute 1h)\n"
            "/unmute — آنمیوت\n"
            "/kick — اخراج\n"
            "/lock یا /قفل — قفل گروه\n"
            "/unlock یا /بازکن — باز کردن گروه\n"
            "/settings — تنظیمات\n"
        )
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
        [btn("حذف استیکر", "delete_stickers"), btn("عضویت اجباری", "force_sub")],
        [InlineKeyboardButton("❌ بستن", callback_data="close_settings")],
    ])


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    await update.message.reply_text(
        "⚙️ **تنظیمات گروه**",
        reply_markup=build_settings_keyboard(update.effective_chat.id),
        parse_mode=ParseMode.MARKDOWN,
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
        set_setting(chat_id, key, 0 if get_setting(chat_id, key, 1) else 1)
        await query.edit_message_reply_markup(reply_markup=build_settings_keyboard(chat_id))


# ============================================
# ⏰ پیام‌های زمانبندی شده
# ============================================

async def scheduled_robot_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text="منم یک روزی نفس می‌کشیدم در جامعه آخرش به ربات تبدیل شدم 🙁🤖",
    )


async def scheduled_owner_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"خیلی نامردی منو تنها گذاشتی تو گروه پیش این غریبه ها 🙄\n{FORCE_SUB_USERNAME}",
    )


async def setup_jobs(app, chat_id: int):
    app.job_queue.run_repeating(
        scheduled_robot_message,
        interval=timedelta(hours=6),
        first=timedelta(hours=6),
        chat_id=chat_id,
        name=f"robot_msg_{chat_id}",
    )
    app.job_queue.run_repeating(
        scheduled_owner_message,
        interval=timedelta(hours=6),
        first=timedelta(hours=3),
        chat_id=chat_id,
        name=f"owner_msg_{chat_id}",
    )


async def on_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                chat_id = update.effective_chat.id
                await setup_jobs(context.application, chat_id)


# ============================================
# 🚀 اجرا
# ============================================

def main():
    init_db()
    app = Application.builder().token(config.TOKEN).build()

    # دستورات ادمین
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))

    # قفل گروه - فارسی و انگلیسی
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("قفل", lock_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("بازکن", unlock_cmd))

    # منو و راهنما
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("join", force_sub_panel))

    # callback ها
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|close_settings)"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))

    # پیام‌ها
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))

    logger.info("🚀 ربات یاشا شروع به کار کرد!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
