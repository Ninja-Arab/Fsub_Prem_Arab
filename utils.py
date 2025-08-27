from datetime import datetime
import telebot
from database import get_user, SessionLocal
import config

def is_user_subscribed(bot, user_id):
    """Cek apakah user sudah subscribe ke channel"""
    try:
        chat_member = bot.get_chat_member(config.PROTECTED_CHANNEL, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

def is_user_premium(user_id):
    """Cek apakah user memiliki akses premium"""
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if user and user.subscription_end and user.subscription_end > datetime.utcnow():
            return True
        return False
    finally:
        db.close()

def format_date(date):
    """Format tanggal menjadi string yang mudah dibaca"""
    if date:
        return date.strftime("%d %B %Y, %H:%M")
    return "Tidak ada"

def format_subscription_status(user):
    """Format status subscription user"""
    if not user.subscription_end:
        return "❌ Tidak aktif"
    
    if user.subscription_end > datetime.utcnow():
        return f"✅ Aktif sampai {format_date(user.subscription_end)}"
    else:
        return f"⚠️ Kadaluarsa pada {format_date(user.subscription_end)}"

def is_admin(user_id):
    """Cek apakah user adalah admin/seller"""
    from database import SessionLocal, Seller
    db = SessionLocal()
    try:
        seller = db.query(Seller).filter(Seller.user_id == user_id).first()
        return seller is not None or user_id in config.OWNER_ID
    finally:
        db.close()

def is_owner(user_id):
    """Cek apakah user adalah owner"""
    return user_id in config.OWNER_ID
