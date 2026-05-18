# group_manager.py
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from telegram import ChatPermissions

logger = logging.getLogger(__name__)


class GroupLock:
    """قفل کردن گروه - فقط ادمین‌ها می‌تونن پیام بدن"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute(self, chat_id: int, admin_id: int) -> Dict[str, Any]:
        try:
            permissions = ChatPermissions(can_send_messages=False)
            await self.bot.set_chat_permissions(chat_id, permissions)
            logger.info(f"Group {chat_id} locked by {admin_id}")
            return {"success": True, "message": "🔒 گروه قفل شد"}
        except Exception as e:
            logger.error(f"Lock failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class GroupUnlock:
    """باز کردن گروه - همه اعضا می‌تونن پیام بدن"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute(self, chat_id: int, admin_id: int) -> Dict[str, Any]:
        try:
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True
            )
            await self.bot.set_chat_permissions(chat_id, permissions)
            logger.info(f"Group {chat_id} unlocked by {admin_id}")
            return {"success": True, "message": "🔓 گروه باز شد"}
        except Exception as e:
            logger.error(f"Unlock failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class UserBan:
    """بن کردن کاربر - حذف کامل از گروه"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int, reason: str = "") -> Dict[str, Any]:
        try:
            await self.bot.ban_chat_member(chat_id, user_id)
            logger.warning(f"User {user_id} banned in {chat_id} by {admin_id} | Reason: {reason}")
            return {"success": True, "message": f"🚫 کاربر {user_id} بن شد"}
        except Exception as e:
            logger.error(f"Ban failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class UserUnban:
    """آنبن کردن کاربر - اجازه بازگشت به گروه"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int) -> Dict[str, Any]:
        try:
            await self.bot.unban_chat_member(chat_id, user_id)
            logger.info(f"User {user_id} unbanned in {chat_id} by {admin_id}")
            return {"success": True, "message": f"✅ کاربر {user_id} آنبن شد"}
        except Exception as e:
            logger.error(f"Unban failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class UserMute:
    """میوت کاربر - سکوت موقت با قابلیت زمان‌بندی"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def parse_time(self, time_str: str) -> Optional[int]:
        """تبدیل رشته زمان به ثانیه (مثال: 1h -> 3600)"""
        match = re.match(r"(\d+)([smhd])", time_str)
        if match:
            val, unit = int(match.group(1)), match.group(2)
            units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            return val * units.get(unit, 1)
        return None
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int, duration_str: str = None) -> Dict[str, Any]:
        try:
            permissions = ChatPermissions(can_send_messages=False)
            until_date = None
            time_text = "برای همیشه"
            
            if duration_str:
                seconds = self.parse_time(duration_str)
                if seconds:
                    until_date = datetime.now() + timedelta(seconds=seconds)
                    time_text = f"به مدت {duration_str}"
            
            await self.bot.restrict_chat_member(chat_id, user_id, permissions=permissions, until_date=until_date)
            logger.info(f"User {user_id} muted {time_text} in {chat_id} by {admin_id}")
            return {"success": True, "message": f"🔇 کاربر {user_id} میوت شد {time_text}"}
        except Exception as e:
            logger.error(f"Mute failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class UserUnmute:
    """آنمیوت کاربر - برداشتن سکوت"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int) -> Dict[str, Any]:
        try:
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True
            )
            await self.bot.restrict_chat_member(chat_id, user_id, permissions=permissions)
            logger.info(f"User {user_id} unmuted in {chat_id} by {admin_id}")
            return {"success": True, "message": f"🔊 کاربر {user_id} آنمیوت شد"}
        except Exception as e:
            logger.error(f"Unmute failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class UserKick:
    """کیک کاربر - اخراج موقت از گروه"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute(self, chat_id: int, user_id: int, admin_id: int) -> Dict[str, Any]:
        try:
            await self.bot.ban_chat_member(chat_id, user_id)
            await self.bot.unban_chat_member(chat_id, user_id)
            logger.info(f"User {user_id} kicked from {chat_id} by {admin_id}")
            return {"success": True, "message": f"👢 کاربر {user_id} کیک شد"}
        except Exception as e:
            logger.error(f"Kick failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class MessagePurge:
    """پاکسازی پیام‌ها - حذف دسته‌جمعی"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def execute(self, chat_id: int, admin_id: int, current_msg_id: int, limit: int = 300) -> Dict[str, Any]:
        try:
            deleted = 0
            for msg_id in range(current_msg_id, max(current_msg_id - limit, 1), -1):
                try:
                    await self.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted += 1
                except:
                    pass
                await asyncio.sleep(0.05)
            logger.info(f"Purged {deleted} messages in {chat_id} by {admin_id}")
            return {"success": True, "deleted": deleted, "message": f"🧹 {deleted} پیام حذف شد"}
        except Exception as e:
            logger.error(f"Purge failed: {e}")
            return {"success": False, "message": f"❌ خطا: {e}"}


class GroupSettings:
    """تنظیمات گروه - ذخیره و بازیابی از دیتابیس"""
    
    DEFAULTS = {
        "welcome_enabled": 1,
        "goodbye_enabled": 1,
        "delete_links": 1,
        "delete_spam": 1,
        "delete_stickers": 0
    }
    
    NAMES = {
        "welcome_enabled": "📝 ولکام",
        "goodbye_enabled": "👋 خداحافظی",
        "delete_links": "🔗 حذف لینک",
        "delete_spam": "🚫 آنتی اسپم",
        "delete_stickers": "🎴 حذف استیکر"
    }
    
    def __init__(self, db):
        self.db = db
    
    def get(self, chat_id: int, key: str) -> int:
        cur = self.db.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key=?",
            (chat_id, key)
        )
        row = cur.fetchone()
        return row[0] if row else self.DEFAULTS.get(key, 0)
    
    def set(self, chat_id: int, key: str, value: int) -> bool:
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, ?, ?)",
                (chat_id, key, value)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Settings save failed: {e}")
            return False
    
    def get_all(self, chat_id: int) -> dict:
        return {key: self.get(chat_id, key) for key in self.DEFAULTS}
    
    def toggle(self, chat_id: int, key: str) -> bool:
        current = self.get(chat_id, key)
        new_value = 0 if current else 1
        return self.set(chat_id, key, new_value)
