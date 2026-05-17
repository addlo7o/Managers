#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v3.0 — Power Edition
# 📌 ربات مدیریت گروه با عضویت اجباری + آنتی اسپم
# ============================================

import asyncio
import logging
import re
from datetime import datetime, timedelta

import config
from database import init_db, get_db, get_setting, set_setting

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== لیست سیاه =====
SPAM_KEYWORDS = ["join", "fast", "سایت", "🔞", "💰", "کلیک", "عضویت"]
FORBIDDEN_DOMAINS = ["bit.ly", "tinyurl.com", "t.me/+"]


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
        [InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")]
        for ch in config.FORCE_SUB_CHANNELS if ch
    ]
    buttons.append([InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_sub")])
    await update.message.reply_text(
        "🔒 برای چت کردن باید عضو کانال‌ها بشی:",
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

async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    chat_id = update.effective_chat.id
    if not get_setting(chat_id, "welcome_enabled", 1):
        return
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        mention = f"[{member.first_name}](tg://user?id={member.id})"
        text = get_setting(chat_id, "welcome_text") or config.WELCOME_DEFAULT
        text = text.replace("{mention}", mention)
        try:
            if config.WELCOME_PIC:
                await context.bot.send_photo(chat_id=chat_id, photo=config.WELCOME_PIC,
                                              caption=text, parse_mode=ParseMode.MARKDOWN)
            else:
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
            permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                        can_send_other_messages=True, can_add_web_page_previews=True),
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
# 🚀 اجرا
# ============================================

def main():
    init_db()
    app = Application.builder().token(config.TOKEN).build()

    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("join", force_sub_panel))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|close_settings)"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))

    logger.info("🚀 ربات یاشا شروع به کار کرد!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
