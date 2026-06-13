#!/usr/bin/env python3
import asyncio
import logging
import re
import os
import random
from datetime import datetime, timedelta

from database import init_db, get_db, get_setting, set_setting

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, BotCommand, MessageEntity
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")

SUDO_USERS = [6387049405]
FORCE_SUB_CHANNEL = "https://t.me/dontworry80"
FORCE_SUB_USERNAME = "@dontworry80"
FORCE_SUB_IDS = [-1002433345751]
GOODBYE_DEFAULT = "😢 {mention} از گروه خارج شد!"

SPAM_KEYWORDS = ["join", "fast", "سایت", "🔞", "💰", "کلیک", "عضویت"]
FORBIDDEN_DOMAINS = ["bit.ly", "tinyurl.com", "t.me/+"]
BAD_WORDS = ["احمق", "خر", "گاو", "کودن", "نادان", "بی‌شعور", "ابله", "حیوان", "مادرجنده", "کصکش", "کیر", "کون", "جنده", "الاغ"]

warnings = {}
active_chats = set()
verified_users = {}

DELETE_DELAY = 30  # ⭐ تغییر به ۳۰ ثانیه

AUTO_MESSAGE_TEXT = "من یک ربات مظلوم مدیریت گروه رایگان هستم \nاین @vzszvx دیونه منو برنامه نویسی کرده هر لحظه ممکن کد منو حذف کن و از کار بیافتم خوبی بدی دیدین حلال کنید کمکککک"

# ============================================
# تابع حذف خودکار
# ============================================
async def auto_delete_message(msg, delay=DELETE_DELAY):
    if msg and delay > 0:
        async def delete_later():
            await asyncio.sleep(delay)
            try:
                await msg.delete()
            except Exception:
                pass
        asyncio.create_task(delete_later())

# ============================================
# لیست شوخی‌های خوش‌آمدگویی
# ============================================
WELCOME_JOKES = [
    "Bienvenue, douce étoile 🌟\nQue ta lumière éclaire notre groupe.",
    "Un nouvel ange est arrivé parmi nous 🕊️\nQue la paix t'accompagne ici.",
    "Bienvenue, belle âme 🌸\nCe jardin t'attendait en silence.",
    "Enfin, le printemps est arrivé 🌷\nEt c'est toi qu'il nous apporte.",
    "Quelle joie de te voir ici 💫\nLe destin t'a guidé vers nous.",
]

# ============================================
# ایموجی‌های پریمیوم
# ============================================
PREMIUM_EMOJIS = {
    1: ("💙", "5377688663960331522"),
    2: ("💙", "5377855630813964361"),
    3: ("😂", "6269133349860677188"),
    4: ("😭", "6269219987940972511"),
    5: ("❤️", "5370897968478047651"),
    6: ("❤️", "5370792982297463610"),
    7: ("🚨", "5379995211722138153"),
    8: ("🌎", "5377357058125340868"),
    9: ("😂", "5920515596088250243"),
    10: ("😁", "5233605022419270727"),
    12: ("✅", "5208880351690112495"),
    14: ("🆒", "5114163768623895481"),
}

AUTO_MESSAGE_EMOJIS = [8, 5]

def get_emoji_utf16_length(emoji: str) -> int:
    return len(emoji.encode('utf-16-le')) // 2

async def send_premium_emoji(chat_id, context, number, reply_to=None):
    if number not in PREMIUM_EMOJIS:
        return None
    text, emoji_id = PREMIUM_EMOJIS[number]
    length = get_emoji_utf16_length(text)
    entities = [MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=length, custom_emoji_id=emoji_id)]
    try:
        msg = await context.bot.send_message(chat_id=chat_id, text=text, entities=entities, reply_to_message_id=reply_to)
        await auto_delete_message(msg)
        return msg
    except Exception as e:
        logger.error(f"Error sending premium emoji {number}: {e}")
        return None

def get_random_emoji():
    return random.choice(list(PREMIUM_EMOJIS.keys()))

def get_random_welcome_joke():
    return random.choice(WELCOME_JOKES)

async def reply_msg(update, text, context, reply_markup=None):
    try:
        msg = await update.message.reply_text(text, reply_markup=reply_markup)
        await auto_delete_message(msg)
        return msg
    except Exception as e:
        logger.error(f"Reply error: {e}")
        return None

async def send_emoji_with_text(chat_id, context, emoji_number, text):
    if emoji_number in PREMIUM_EMOJIS:
        emoji_text, emoji_id = PREMIUM_EMOJIS[emoji_number]
        length = get_emoji_utf16_length(emoji_text)
        entities = [MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=length, custom_emoji_id=emoji_id)]
        try:
            msg = await context.bot.send_message(chat_id=chat_id, text=emoji_text, entities=entities)
            await auto_delete_message(msg)
        except Exception as e:
            logger.error(f"Error sending emoji {emoji_number}: {e}")
    
    try:
        msg = await context.bot.send_message(chat_id=chat_id, text=text)
        await auto_delete_message(msg)
    except Exception as e:
        logger.error(f"Error sending text: {e}")

# ============================================
# پیام خودکار هر نیم ساعت
# ============================================
async def auto_message_job(context: ContextTypes.DEFAULT_TYPE):
    if not active_chats:
        return
    
    for chat_id in list(active_chats):
        try:
            emoji_num = random.choice(AUTO_MESSAGE_EMOJIS)
            await send_emoji_with_text(chat_id, context, emoji_num, AUTO_MESSAGE_TEXT)
            await asyncio.sleep(2)
        except Exception as e:
            error_str = str(e).lower()
            if "chat not found" in error_str or "kicked" in error_str:
                active_chats.discard(chat_id)

# ============================================
# عضویت اجباری
# ============================================
async def is_force_subscribed(user_id, context):
    """بررسی میکنه کاربر عضو کانال هست یا نه"""
    if user_id in verified_users:
        last_check = verified_users[user_id]
        if datetime.now() - last_check < timedelta(minutes=5):
            return True
    
    for ch_id in FORCE_SUB_IDS:
        if ch_id == 0:
            continue
        try:
            member = await context.bot.get_chat_member(ch_id, user_id)
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                verified_users.pop(user_id, None)
                return False
            elif member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, 
                                    ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED]:
                verified_users[user_id] = datetime.now()
                return True
        except:
            pass
    return False

async def restrict_user(chat_id, user_id, user_name, context):
    """میوت کردن کاربر"""
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        
        buttons = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)],
            [InlineKeyboardButton("🔄 بررسی عضویت", callback_data=f"check_sub_{user_id}")]
        ]
        text = (
            f"👤 {user_name} عزیز، خوش اومدی!\n\n"
            f"🔒 برای چت کردن تو این گروه، اول باید عضو کانال {FORCE_SUB_USERNAME} بشی.\n"
            f"بعد از عضویت، دکمه «بررسی عضویت» رو بزن تا چت برات باز بشه."
        )
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await auto_delete_message(msg, 60)
        return True
    except Exception as e:
        logger.error(f"Error restricting user {user_id}: {e}")
        return False

async def unrestrict_user(chat_id, user_id, context):
    """آنمیوت کردن کاربر"""
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True
            )
        )
        return True
    except Exception as e:
        logger.error(f"Error unrestricting user {user_id}: {e}")
        return False

# ============================================
# ولکام - فقط کاربرای عضو کانال
# ============================================
welcome_counter = {}

async def welcome_member(update, context):
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = update.effective_chat.id
    active_chats.add(chat_id)
    
    if chat_id not in welcome_counter:
        welcome_counter[chat_id] = 0
    
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        is_subscribed = await is_force_subscribed(member.id, context)
        
        if not is_subscribed:
            # عضو کانال نیست → محدودش کن
            await restrict_user(chat_id, member.id, member.first_name, context)
            
            # پیام راهنما
            text = (
                f"👤 **{member.first_name}** عزیز!\n\n"
                f"🔒 برای چت کردن، لطفاً عضو کانال {FORCE_SUB_USERNAME} بشید.\n"
                f"بعد از عضویت، دکمه «بررسی عضویت» رو بزنید."
            )
        else:
            # عضو کانال هست → ولکام عادی
            welcome_counter[chat_id] += 1
            random_emoji_num = get_random_emoji()
            await send_premium_emoji(chat_id, context, random_emoji_num)
            joke = get_random_welcome_joke()
            text = f"👤 **{member.first_name}**\n🆔 `{member.id}`\n\n{joke}"
        
        try:
            msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
            await auto_delete_message(msg)
        except:
            pass

async def goodbye_member(update, context):
    if not update.message or not update.message.left_chat_member:
        return
    chat_id = update.effective_chat.id
    member = update.message.left_chat_member
    text = GOODBYE_DEFAULT.replace("{mention}", member.first_name)
    try:
        msg = await context.bot.send_message(chat_id=chat_id, text=text)
        await auto_delete_message(msg)
    except:
        pass

# ============================================
# هندلر اصلی پیام‌ها
# ============================================
async def message_handler(update, context):
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    
    # ادمین‌ها و سودو آزادن
    if user_id in SUDO_USERS:
        return
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except:
        pass
    
    # چک عضویت کانال
    if not await is_force_subscribed(user_id, context):
        # حذف پیام
        try:
            await update.message.delete()
        except:
            pass
        
        # محدود کردن کاربر
        await restrict_user(chat_id, user_id, user.first_name, context)
        return
    
    # کاربر عضو کانال هست → بررسی آنتی اسپم
    if update.message.text:
        await anti_spam(update, context)

# ============================================
# آنتی اسپم
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
                    msg = await context.bot.send_message(chat_id=chat_id, text=f"🔇 {update.effective_user.first_name} بعد از ۵ اخطار سکوت شد!")
                    await auto_delete_message(msg)
                    warnings[key] = 0
                except:
                    pass
            else:
                msg = await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {update.effective_user.first_name} اخطار {count}/5")
                await auto_delete_message(msg)
            try:
                await update.message.delete()
            except:
                pass
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
    
    for domain in FORBIDDEN_DOMAINS:
        if domain in msg_text:
            try:
                await update.message.delete()
            except:
                pass
            msg = await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {update.effective_user.first_name} لینک ممنوع ارسال کرد!")
            await auto_delete_message(msg)
            return
    
    for word in SPAM_KEYWORDS:
        if word in msg_text:
            try:
                await update.message.delete()
            except:
                pass
            return
    
    await anti_bad_words(update, context)

# ============================================
# دستورات مدیریتی
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

async def lock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=False))
        await reply_msg(update, "🔒 گروه قفل شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def unlock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True))
        await reply_msg(update, "🔓 گروه باز شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def ban_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await reply_msg(update, f"🚫 {target.first_name} بن شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def unban_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await reply_msg(update, f"✅ {target.first_name} آنبن شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def mute_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
        await reply_msg(update, f"🔇 {target.first_name} میوت شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def unmute_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await reply_msg(update, f"🔊 {target.first_name} آنمیوت شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def kick_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await reply_msg(update, f"👢 {target.first_name} کیک شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

# ============================================
# کالبک بررسی عضویت
# ============================================
async def check_sub_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    # user_id رو از callback_data استخراج کن
    callback_data = query.data
    
    if callback_data == "check_sub":
        # برای کاربری که دکمه رو زده
        user_id = query.from_user.id
    elif callback_data.startswith("check_sub_"):
        user_id = int(callback_data.split("_")[2])
    else:
        return
    
    chat_id = query.message.chat_id
    
    if await is_force_subscribed(user_id, context):
        # عضو شده → باز کردن چت
        success = await unrestrict_user(chat_id, user_id, context)
        if success:
            await query.edit_message_text("✅ عضویت تأیید شد! چت برات باز شد. خوش اومدی! 🎉")
        else:
            await query.edit_message_text("❌ خطا در باز کردن چت. لطفاً به ادمین پیام بده.")
        await auto_delete_message(query.message, 10)
    else:
        await query.answer("❌ هنوز عضو نشدی! لطفاً اول عضو کانال بشو.", show_alert=True)

async def close_menu(update, context):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

# ============================================
# Main
# ============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    init_db()
    
    # JobQueue برای پیام خودکار
    app.job_queue.run_repeating(auto_message_job, interval=1800, first=10)
    
    # دستورات
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    
    # کالبک‌ها
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub"))
    app.add_handler(CallbackQueryHandler(close_menu, pattern="^close"))
    
    # هندلرهای گروه
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    
    # هندلر اصلی پیام‌ها
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.Sticker.ALL | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        message_handler
    ))
    
    print("🤖 ربات آماده!")
    print(f"⏱️ پیام‌ها بعد از {DELETE_DELAY} ثانیه حذف میشن")
    print(f"🔒 کاربرا باید عضو {FORCE_SUB_USERNAME} باشن")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

async def start_cmd(update, context):
    buttons = [
        [InlineKeyboardButton("📢 کانال ما", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("❌ بستن", callback_data="close")]
    ]
    await reply_msg(update, "🤖 **ربات مدیریت گروه**\n\nبرای چت آزاد باید عضو کانال باشید.", context, reply_markup=InlineKeyboardMarkup(buttons))

async def help_cmd(update, context):
    text = """
📋 **راهنمای ربات**

/lock - قفل گروه
/unlock - باز کردن گروه
/ban - بن کاربر
/unban - آنبن کاربر
/mute - میوت کاربر
/unmute - آنمیوت کاربر
/kick - کیک کاربر
"""
    await reply_msg(update, text, context)

if __name__ == "__main__":
    main()
