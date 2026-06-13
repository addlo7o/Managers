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

# دیکشنری برای ذخیره کاربران تأییدشده در مموری
verified_users = {}

DELETE_DELAY = 50

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
    "Bienvenue, poète du cœur 📜\nÉcris ton histoire avec nous.",
    "Un rayon de soleil est entré ☀️\nEt ce rayon, c'est toi.",
    "Bienvenue, mystérieux voyageur 🌙\nIci, chaque rêve est possible.",
    "La douceur a un nouveau visage 🍯\nEt c'est le tien, bienvenue.",
    "Bienvenue, trésor caché 💎\nEnfin, on t'a découvert.",
    "Que cette maison soit la tienne 🏡\nEntre et pose tes ailes.",
    "Bienvenue, souffle du vent 🍃\nRafraîchis nos âmes fatiguées.",
    "L'univers nous a fait un cadeau 🎁\nEt ce cadeau, c'est toi.",
    "Bienvenue, mélodie silencieuse 🎵\nQue ta musique enchante nos jours.",
    "Une fleur rare vient d'éclore 🌺\nIci même, parmi nous.",
    "Bienvenue, âme vagabonde 🌊\nTrouve ici ton rivage paisible.",
    "Le ciel est plus bleu aujourd'hui 🔵\nCar tu es parmi nous.",
    "Bienvenue, doux mystère ✨\nRévèle-toi lentement à nous.",
    "Un papillon s'est posé ici 🦋\nReste, la beauté t'appartient.",
    "Bienvenue, dernier rayon du soir 🌅\nRéchauffe nos cœurs avant la nuit.",
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
    11: ("☔️", "5240242851425559175"),
    12: ("✅", "5208880351690112495"),
    13: ("🦋", "6037196272539011616"),
    14: ("🆒", "5114163768623895481"),
    15: ("🧪", "5294271852087100131"),
    16: ("🫥", "5307937750828194743"),
    17: ("🎰", "5415683280395585071"),
    18: ("✍️", "5931757569906314192"),
    19: ("😔", "5436083339964460643"),
    20: ("😭", "5380070541153541181"),
}

AUTO_MESSAGE_EMOJIS = [19, 20]

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

async def reply_msg(update, text, context, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    try:
        msg = await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        await auto_delete_message(msg)
        return msg
    except Exception as e:
        logger.error(f"Reply error: {e}")
        return None

async def send_emoji_with_text(chat_id, context, emoji_number, text, parse_mode=ParseMode.MARKDOWN):
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
        msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        await auto_delete_message(msg)
    except Exception as e:
        logger.error(f"Error sending text: {e}")

# ============================================
# پیام خودکار هر نیم ساعت با JobQueue
# ============================================
async def auto_message_job(context: ContextTypes.DEFAULT_TYPE):
    if not active_chats:
        return
    
    logger.info(f"Sending auto message to {len(active_chats)} groups...")
    for chat_id in list(active_chats):
        try:
            emoji_num = random.choice(AUTO_MESSAGE_EMOJIS)
            await send_emoji_with_text(chat_id, context, emoji_num, AUTO_MESSAGE_TEXT)
            await asyncio.sleep(2)
        except Exception as e:
            error_str = str(e).lower()
            if "chat not found" in error_str or "bot was kicked" in error_str or "kicked" in error_str:
                active_chats.discard(chat_id)
                logger.warning(f"Removed {chat_id} from active_chats")
            else:
                logger.error(f"Failed to send auto message to {chat_id}: {e}")

# ============================================
# عضویت اجباری - توابع اصلی
# ============================================
async def is_force_subscribed(user_id, context):
    """بررسی کن که کاربر عضو کانال هست یا نه"""
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
        except Exception as e:
            logger.error(f"Error checking subscription for {user_id}: {e}")
            return True
    return False

async def restrict_user_for_not_subscribed(chat_id, user_id, user_name, context):
    """میوت کردن کاربری که عضو کانال نیست"""
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(days=365)
        )
        
        buttons = [[InlineKeyboardButton("📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)]]
        text = (
            f"👤 {user_name} عزیز، خوش اومدی!\n\n"
            f"🔒 برای چت کردن تو این گروه، اول باید عضو کانال {FORCE_SUB_USERNAME} بشی.\n"
            f"بعد از عضویت، چت به‌طور خودکار برات باز میشه.\n"
            f"اگه از کانال خارج بشی، دوباره چت برات بسته میشه."
        )
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await auto_delete_message(msg, 120)
        return True
    except Exception as e:
        logger.error(f"Error restricting user {user_id}: {e}")
        return False

async def check_and_handle_new_message(update, context):
    """بررسی هر پیام جدید و بلاک کردن غیرمشترکین"""
    if not update.message:
        return "ALLOWED"
    
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_id = user.id
    
    if user_id in SUDO_USERS:
        return "ALLOWED"
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return "ALLOWED"
    except:
        pass
    
    if not await is_force_subscribed(user_id, context):
        try:
            await update.message.delete()
        except:
            pass
        
        await restrict_user_for_not_subscribed(chat_id, user_id, user.first_name, context)
        return "BLOCKED"
    
    return "ALLOWED"

# ============================================
# ولکام و خداحافظی
# ============================================
welcome_counter = {}

async def welcome_member(update, context):
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = update.effective_chat.id
    active_chats.add(chat_id)
    
    if not get_setting(chat_id, "welcome_enabled", 1):
        return
    
    if chat_id not in welcome_counter:
        welcome_counter[chat_id] = 0
    
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        is_subscribed = await is_force_subscribed(member.id, context)
        
        if not is_subscribed:
            await restrict_user_for_not_subscribed(chat_id, member.id, member.first_name, context)
            
            joke = get_random_welcome_joke()
            text = (
                f"👤 **{member.first_name}**\n"
                f"🆔 `{member.id}`\n\n"
                f"⚠️ برای چت کردن، لطفاً عضو کانال {FORCE_SUB_USERNAME} بشید.\n"
                f"بعد از عضویت، چت به‌طور خودکار باز میشه.\n\n"
                f"{joke}"
            )
        else:
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
    if not get_setting(chat_id, "goodbye_enabled", 1):
        return
    member = update.message.left_chat_member
    mention = member.first_name
    text = get_setting(chat_id, "goodbye_text") or GOODBYE_DEFAULT
    text = text.replace("{mention}", mention)
    try:
        msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
        await auto_delete_message(msg)
    except:
        pass

# ============================================
# هندلر پیام جدید - چک عضویت + آنتی اسپم
# ============================================
async def message_handler(update, context):
    """هندلر اصلی پیام‌ها"""
    if not update.message or not update.effective_user:
        return
    
    result = await check_and_handle_new_message(update, context)
    
    if result == "BLOCKED":
        return
    
    if update.message.text:
        await anti_spam(update, context)

# ============================================
# آنتی اسپم و بدزبانی
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
                msg = await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {update.effective_user.first_name} لینک ممنوع ارسال کرد!")
                await auto_delete_message(msg)
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
# بررسی ادمین
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
# دستورات مدیریتی
# ============================================
async def lock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=False))
        await send_premium_emoji(update.effective_chat.id, context, 12)
        await reply_msg(update, "🔒 گروه قفل شد! فقط ادمین‌ها می‌تونن پیام بدن.", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def unlock_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    try:
        await context.bot.set_chat_permissions(update.effective_chat.id, ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_send_polls=True))
        await send_premium_emoji(update.effective_chat.id, context, 12)
        await reply_msg(update, "🔓 گروه باز شد! همه می‌تونن پیام بدن.", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def ban_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await send_premium_emoji(update.effective_chat.id, context, 7)
        await reply_msg(update, f"🚫 **{target.first_name}** بن شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def unban_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await send_premium_emoji(update.effective_chat.id, context, 12)
        await reply_msg(update, f"✅ **{target.first_name}** آنبن شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def mute_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن\nمثال: /mute 1h", context)
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
                await send_premium_emoji(update.effective_chat.id, context, 1)
                await reply_msg(update, f"🔇 **{target.first_name}** میوت شد برای {duration}!", context)
            else:
                await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
                await reply_msg(update, f"🔇 **{target.first_name}** میوت دائمی شد!", context)
        else:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=False))
            await reply_msg(update, f"🔇 **{target.first_name}** میوت دائمی شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def unmute_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await send_premium_emoji(update.effective_chat.id, context, 12)
        await reply_msg(update, f"🔊 **{target.first_name}** آنمیوت شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def kick_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    target = get_target_user(update)
    if not target:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await send_premium_emoji(update.effective_chat.id, context, 7)
        await reply_msg(update, f"👢 **{target.first_name}** کیک شد!", context)
    except Exception as e:
        await reply_msg(update, f"❌ خطا: {e}", context)

async def purge_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    chat_id = update.effective_chat.id
    current = update.message.message_id
    deleted = 0
    await reply_msg(update, "🧹 در حال پاکسازی...", context)
    for msg_id in range(current, max(current - 200, 1), -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except:
            pass
        await asyncio.sleep(0.05)
    await send_premium_emoji(chat_id, context, 12)
    await reply_msg(update, f"✅ پاکسازی تموم شد! {deleted} پیام حذف شد.", context)

async def purge_user_cmd(update, context):
    if not await is_admin(update, context):
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    if not update.message.reply_to_message:
        await reply_msg(update, "❌ روی پیام کاربر reply کن", context)
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
    await reply_msg(update, f"✅ {deleted} پیام از {target.first_name} حذف شد.", context)

# ============================================
# تنظیمات
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
        await reply_msg(update, "❌ فقط ادمین‌ها!", context)
        return
    active_chats.add(update.effective_chat.id)
    await reply_msg(update, "⚙️ تنظیمات گروه", context, reply_markup=build_settings_keyboard(update.effective_chat.id))

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
# منو و استارت
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

🗑 /purge - پاک کردن پیام‌ها
👤 /purgeuser - پاک کردن پیام‌های کاربر

━━━━━━━━━━━━━━━━━━━━━━
⚙️ **دستورات عمومی**
━━━━━━━━━━━━━━━━━━━━━━

🎯 /start - منوی اصلی
❓ /help - راهنما
⚙️ /settings - تنظیمات گروه
📢 /join - بررسی عضویت
"""

async def start_cmd(update, context):
    if not await is_force_subscribed(update.effective_user.id, context):
        await force_sub_panel(update, context)
        return
    active_chats.add(update.effective_chat.id)
    buttons = [
        [InlineKeyboardButton("📋 راهنما", callback_data="menu_help")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="menu_settings")],
        [InlineKeyboardButton("📢 کانال ما", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("❌ بستن", callback_data="close_menu")],
    ]
    await send_premium_emoji(update.effective_chat.id, context, 14)
    await reply_msg(update, "🤖 **ربات مدیریت گروه یاشا**\n\nاز منوی زیر استفاده کن:", context, reply_markup=InlineKeyboardMarkup(buttons))

async def help_cmd(update, context):
    active_chats.add(update.effective_chat.id)
    await reply_msg(update, get_help_text(), context)

async def join_cmd(update, context):
    await force_sub_panel(update, context)

async def force_sub_panel(update, context):
    user = update.effective_user
    if await is_force_subscribed(user.id, context):
        await reply_msg(update, "✅ عضویت تأیید شد! چت برات بازه 🎉", context)
        try:
            chat_id = update.effective_chat.id
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
        except:
            pass
        return
    buttons = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=FORCE_SUB_CHANNEL)],
        [InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_sub")]
    ]
    await reply_msg(
        update,
        f"🔒 برای استفاده از ربات و چت در گروه، باید عضو کانال {FORCE_SUB_USERNAME} بشی:\n"
        f"بعد از عضویت، چت به‌طور خودکار برات باز میشه.",
        context,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def check_sub_callback(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    if await is_force_subscribed(user_id, context):
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
        except:
            pass
        
        await query.edit_message_text("✅ عضویت تأیید شد! چت برات باز شد. خوش اومدی! 🎉")
        await auto_delete_message(query.message, 10)
    else:
        await query.answer("❌ هنوز عضو نشدی! لطفاً اول عضو کانال بشو.", show_alert=True)

async def menu_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "menu_help":
        await query.edit_message_text(get_help_text(), parse_mode=ParseMode.MARKDOWN)
        await auto_delete_message(query.message)
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
    app = Application.builder().token(BOT_TOKEN).build()
    
    init_db()
    
    # JobQueue برای پیام خودکار
    app.job_queue.run_repeating(
        auto_message_job,
        interval=1800,
        first=10
    )
    
    # هندلرهای دستورات
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("join", join_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("purge", purge_cmd))
    app.add_handler(CommandHandler("purgeuser", purge_user_cmd))
    
    # هندلرهای کالبک
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(toggle_|close_settings)"))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="^(menu_|close_menu)"))
    
    # هندلرهای گروه
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    
    # ⭐ هندلر اصلی پیام‌ها
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.Sticker.ALL | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        message_handler
    ))
    
    # تنظیم کامندها
    app.post_init = set_bot_commands
    
    print("🤖 ربات یاشا آماده‌ست!")
    print("✨ اعضای جدید باید عضو @dontworry80 بشن تا چت کنن")
    print("🔒 پیام غیرمشترکین حذف و میوت میشن")
    print("🔓 بعد از عضویت، چت خودکار باز میشه")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
