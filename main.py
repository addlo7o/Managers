#!/usr/bin/env python3
# ============================================
# 🚀 Yasha Group Bot v4.1 — Fixed Edition
# ============================================

import asyncio
import logging
import re
from datetime import datetime, timedelta

import config
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
# ✨ Custom Emoji IDs (پرمیوم)
# ============================================

CUSTOM_EMOJI_IDS = [
    "5370695190187105084",
    "5370579513832921134",
    "5370968375876931435",
    "5370985117659448492",
    "5377855630813964361",
    "5379833622167559121",
    "5377486534209446615",
    "5377357058125340868",
    "5474311022800029635",
    "5233605022419270727",
]

# ایموجی‌های متناظر (placeholder برای نمایش)
CUSTOM_EMOJI_CHARS = ["📛", "❤️", "❤️", "👑", "💙", "💙", "🔥", "🌎", "😹", "😁"]

def build_custom_emoji_entities(text: str, start_offset: int = 0):
    """
    ساخت entities برای custom emoji
    هر ایموجی 2 بایت در متن
    """
    entities = []
    for i, emoji_id in enumerate(CUSTOM_EMOJI_IDS):
        offset = start_offset + (i * 2)
        if offset + 2 > len(text.encode('utf-16-le')) // 2:
            break
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=offset,
                length=2,
                custom_emoji_id=emoji_id,
            )
        )
    return entities


def get_emoji_prefix() -> str:
    """پیشوند ایموجی پرمیوم برای پیام‌ها"""
    # این رشته شامل کاراکترهای unicode ایموجی است
    return "\U0001f4db\u2764\ufe0f\u2764\ufe0f\U0001f451\U0001f499\U0001f499\U0001f525\U0001f30e\U0001f639\U0001f601"


async def send_premium_message(chat_id, text: str, context: ContextTypes.DEFAULT_TYPE,
                                reply_to_message_id=None, parse_mode=ParseMode.MARKDOWN):
    """
    ارسال پیام با custom emoji entities پرمیوم
    """
    emoji_prefix = get_emoji_prefix()
    full_text = emoji_prefix + "\n" + text

    # ساخت entities برای custom emoji در پیشوند
    entities = []
    offset = 0
    emoji_pairs = [
        ("5370695190187105084", 2),
        ("5370579513832921134", 2),
        ("5370968375876931435", 2),
        ("5370985117659448492", 2),
        ("5377855630813964361", 2),
        ("5379833622167559121", 2),
        ("5377486534209446615", 2),
        ("5377357058125340868", 2),
        ("5474311022800029635", 2),
        ("5233605022419270727", 2),
    ]
    for emoji_id, length in emoji_pairs:
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=offset,
                length=length,
                custom_emoji_id=emoji_id,
            )
        )
        offset += length

    try:
        return await context.bot.send_message(
            chat_id=chat_id,
            text=full_text,
            entities=entities,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception:
        # fallback بدون entities
        return await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
        )


async def reply_premium(update: Update, text: str, context: ContextTypes.DEFAULT_TYPE,
                         reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    """
    reply با custom emoji
    """
    emoji_prefix = get_emoji_prefix()
    full_text = emoji_prefix + "\n" + text

    entities = []
    offset = 0
    emoji_data = [
        ("5370695190187105084", 2),
        ("5370579513832921134", 2),
        ("5370968375876931435", 2),
        ("5370985117659448492", 2),
        ("5377855630813964361", 2),
        ("5379833622167559121", 2),
        ("5377486534209446615", 2),
        ("5377357058125340868", 2),
        ("5474311022800029635", 2),
        ("5233605022419270727", 2),
    ]
    for emoji_id, length in emoji_data:
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=offset,
                length=length,
                custom_emoji_id=emoji_id,
            )
        )
        offset += length

    try:
        return await update.message.reply_text(
            full_text,
            entities=entities,
            reply_markup=reply_markup,
        )
    except Exception:
        return await update.message.reply_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )


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

        text = (
            f"👤 **{member.first_name}**\n"
            f"🆔 `{member.id}`\n"
            f"👋 {greeting}"
        )
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
    text = get_setting(chat_id, "goodbye_text") or config.GOODBYE_DEFAULT
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
                    f"⚠️ [{update.effective_user.first_name}](tg://user?id={user_id}) مراقب زبونت باش!\n"
                    f"🔴 اخطار: {count}/20",
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

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
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
        return
    try:
        # ✅ FIX: حذف can_send_media_messages که در نسخه جدید PTB وجود نداره
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
# 🧹 پاکسازی پیام‌های ۴۸ ساعت گذشته
# ============================================

async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /purge — پاک کردن همه پیام‌های ۴۸ ساعت گذشته
    فقط ادمین‌ها می‌تونن استفاده کنن
    """
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها می‌تونن این دستور رو بزنن!", context)
        return

    chat_id = update.effective_chat.id
    cutoff_time = datetime.now() - timedelta(hours=48)
    deleted = 0
    failed = 0

    status_msg = await reply_premium(update, "🧹 در حال پاکسازی پیام‌های ۴۸ ساعت گذشته...", context)

    # telegram فقط اجازه میده پیام‌های تا ۴۸ ساعت پاک بشن
    # باید از message_id فعلی به عقب برگردیم
    current_msg_id = update.message.message_id

    # تلاش برای حذف پیام‌ها از آخرین ID به عقب
    for msg_id in range(current_msg_id, max(current_msg_id - 5000, 0), -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except Exception:
            failed += 1
            # اگر ۵۰ پیام پشت سر هم fail شد، احتمالاً رسیدیم به قبل از ۴۸ ساعت
            if failed > 50:
                break
        await asyncio.sleep(0.05)  # جلوگیری از rate limit

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ پاکسازی تموم شد!\n🗑 {deleted} پیام حذف شد.",
        )
    except Exception:
        pass


async def purge_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /purgeuser — پاک کردن پیام‌های یک کاربر خاص (reply یا ID)
    """
    if not await is_admin(update, context):
        await reply_premium(update, "❌ فقط ادمین‌ها می‌تونن این دستور رو بزنن!", context)
        return

    user = await get_target(update, context)
    if not user:
        await reply_premium(update, "❌ روی پیام کاربر reply کن یا ID بده", context)
        return

    chat_id = update.effective_chat.id
    current_msg_id = update.message.message_id
    deleted = 0

    status_msg = await reply_premium(
        update,
        f"🧹 در حال پاک کردن پیام‌های {user.first_name}...",
        context,
    )

    # تلگرام اطلاعات message owner نداره از طریق bot API
    # بهترین راه اینه که بریم عقب و حذف کنیم
    for msg_id in range(current_msg_id, max(current_msg_id - 3000, 0), -1):
        try:
            msg = await context.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=msg_id,
                disable_notification=True,
            )
            if msg.forward_from and msg.forward_from.id == user.id:
                await context.bot.delete_message(chat_id, msg_id)
                deleted += 1
            await context.bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        await asyncio.sleep(0.05)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ {deleted} پیام از {user.first_name} حذف شد.",
        )
    except Exception:
        pass


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
        # ✅ FIX: حذف can_send_media_messages
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
        "/lock یا /قفل — قفل کردن گروه\n"
        "/unlock یا /بازکن — باز کردن گروه\n\n"
        "🧹 **پاکسازی:**\n"
        "/purge — پاک کردن پیام‌های ۴۸ ساعت گذشته\n"
        "/purgeuser — پاک کردن پیام‌های یک کاربر خاص\n\n"
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
        text = (
            "📋 **دستورات ربات:**\n\n"
            "/ban — بن کردن\n"
            "/unban — آنبن کردن\n"
            "/mute — میوت (مثال: /mute 1h)\n"
            "/unmute — آنمیوت\n"
            "/kick — اخراج\n"
            "/lock یا /قفل — قفل گروه\n"
            "/unlock یا /بازکن — باز کردن گروه\n"
            "/purge — پاکسازی ۴۸ ساعت\n"
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
        set_setting(chat_id, key, 0 if get_setting(chat_id, key, 1) else 1)
        await query.edit_message_reply_markup(reply_markup=build_settings_keyboard(chat_id))


# ============================================
# ⏰ پیام‌های زمانبندی شده
# ============================================

async def scheduled_robot_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await send_premium_message(
        chat_id,
        "منم یک روزی نفس می‌کشیدم در جامعه آخرش به ربات تبدیل شدم 🙁🤖",
        context,
    )


async def scheduled_owner_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    await send_premium_message(
        chat_id,
        f"خیلی نامردی منو تنها گذاشتی تو گروه پیش این غریبه ها 🙄\n{FORCE_SUB_USERNAME}",
        context,
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
                await send_premium_message(
                    chat_id,
                    "👋 سلام! ربات یاشا آماده‌ست!\nبرای راهنما /help بزن.",
                    context,
                )


# ============================================
# 🚀 اجرای ربات
# ============================================

def main():
    init_db()
    app = Application.builder().token(config.BOT_TOKEN).build()

    # دستورات
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler(["lock", "قفل"], lock_cmd))
    app.add_handler(CommandHandler(["unlock", "بازکن"], unlock_cmd))
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
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))

    logger.info("✅ ربات یاشا v4.1 شروع به کار کرد!")
    app.run_polling()


if __name__ == "__main__":
    main()
