import telebot
from telebot import types
from datetime import datetime, timedelta
import schedule
import time
import threading
from database import (
    SessionLocal, get_user, create_user, update_subscription, 
    get_sellers, add_seller, remove_seller, get_buttons, 
    add_button, remove_button, update_button, get_stats,
    log_purchase, log_subscription, get_users_expiring_soon,
    update_last_notified
)
import config
import logger
from utils import is_user_subscribed, is_user_premium, format_subscription_status, is_admin, is_owner

# Inisialisasi bot
bot = telebot.TeleBot(config.BOT_TOKEN)

# Fungsi untuk mengirim notifikasi ke owner
def notify_owner(message):
    try:
        for owner_id in config.OWNER_ID:
            bot.send_message(owner_id, message)
    except Exception as e:
        logger.log_error(f"Gagal mengirim notifikasi ke owner: {e}")

# Fungsi untuk memeriksa subscription yang akan kadaluarsa
def check_expiring_subscriptions():
    db = SessionLocal()
    try:
        expiring_users = get_users_expiring_soon(db)
        for user in expiring_users:
            try:
                days_left = (user.subscription_end - datetime.utcnow()).days
                message = f"⚠️ Peringatan: Subscription Anda akan kadaluarsa dalam {days_left} hari."
                bot.send_message(user.user_id, message)
                update_last_notified(db, user.user_id)
                logger.log_activity(user.user_id, "expiration_warning_sent", f"{days_left} days left")
            except Exception as e:
                logger.log_error(f"Gagal mengirim notifikasi ke user {user.user_id}: {e}")
    finally:
        db.close()

# Fungsi untuk menjalankan penjadwalan
def run_scheduler():
    schedule.every().day.at("09:00").do(check_expiring_subscriptions)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Mulai penjadwalan di thread terpisah
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

# Handler untuk command /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    db = SessionLocal()
    try:
        # Buat atau dapatkan user
        user = get_user(db, message.from_user.id)
        if not user:
            user = create_user(
                db, 
                message.from_user.id, 
                message.from_user.username, 
                message.from_user.full_name
            )
            logger.log_activity(message.from_user.id, "new_user_registered")
        
        # Buat keyboard dengan tombol dinamis
        markup = types.InlineKeyboardMarkup()
        buttons = get_buttons(db)
        for button in buttons:
            markup.add(types.InlineKeyboardButton(button.name, url=button.url))
        
        # Tambahkan tombol untuk cek status
        markup.add(types.InlineKeyboardButton("📊 Cek Status", callback_data="check_status"))
        
        welcome_text = f"""
👋 Halo {message.from_user.first_name}!

Selamat datang di bot premium kami. Untuk mengakses konten premium, Anda perlu:
1. Subscribe ke channel kami: {config.PROTECTED_CHANNEL}
2. Memiliki subscription aktif

Gunakan tombol di bawah untuk mengakses konten.
        """
        
        bot.reply_to(message, welcome_text, reply_markup=markup)
        logger.log_activity(message.from_user.id, "started_bot")
    finally:
        db.close()

# Handler untuk callback
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    db = SessionLocal()
    try:
        if call.data == "check_status":
            user = get_user(db, call.from_user.id)
            if user:
                status_text = f"""
📊 Status Keanggotaan Anda:

Nama: {user.full_name}
Username: @{user.username or 'Tidak ada'}
Tanggal Bergabung: {user.joined_at.strftime('%d %B %Y')}
Status Subscription: {format_subscription_status(user)}
                """
                
                # Jika subscription aktif, beri akses
                if is_user_premium(call.from_user.id) and is_user_subscribed(bot, call.from_user.id):
                    status_text += "\n\n✅ Anda memiliki akses premium!"
                    # Tambahkan tombol konten premium di sini
                else:
                    status_text += "\n\n❌ Anda tidak memiliki akses premium saat ini."
                
                bot.answer_callback_query(call.id, "Status diperbarui")
                bot.edit_message_text(status_text, call.message.chat.id, call.message.message_id)
            logger.log_activity(call.from_user.id, "checked_status")
        
        elif call.data == "admin_panel":
            if is_admin(call.from_user.id):
                show_admin_panel(call.message)
            else:
                bot.answer_callback_query(call.id, "❌ Akses ditolak!")
        
        elif call.data.startswith("add_days_"):
            if is_admin(call.from_user.id):
                # Format: add_days_userId_days
                parts = call.data.split("_")
                if len(parts) == 4:
                    target_user_id = int(parts[2])
                    days = int(parts[3])
                    updated_user = update_subscription(db, target_user_id, days)
                    if updated_user:
                        log_subscription(db, target_user_id, call.from_user.id, days)
                        bot.answer_callback_query(call.id, f"✅ Berhasil menambah {days} hari subscription!")
                        notify_owner(f"📥 Penambahan subscription: {days} hari untuk user {target_user_id} oleh {call.from_user.id}")
                    else:
                        bot.answer_callback_query(call.id, "❌ Gagal menambah subscription!")
            else:
                bot.answer_callback_query(call.id, "❌ Akses ditolak!")
    finally:
        db.close()

# Handler untuk command /admin
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if is_admin(message.from_user.id):
        show_admin_panel(message)
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

def show_admin_panel(message):
    markup = types.InlineKeyboardMarkup()
    
    # Tombol berdasarkan level akses
    if is_owner(message.from_user.id):
        markup.add(types.InlineKeyboardButton("👥 Kelola Seller", callback_data="manage_sellers"))
        markup.add(types.InlineKeyboardButton("🔘 Kelola Tombol", callback_data="manage_buttons"))
    
    markup.add(types.InlineKeyboardButton("📊 Statistik", callback_data="show_stats"))
    markup.add(types.InlineKeyboardButton("➕ Tambah Subscription", callback_data="add_subscription"))
    markup.add(types.InlineKeyboardButton("📤 Broadcast", callback_data="broadcast"))
    
    bot.reply_to(message, "🔧 Panel Admin", reply_markup=markup)

# Handler untuk command /broadcast
@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if is_admin(message.from_user.id):
        msg = bot.reply_to(message, "📢 Kirim pesan yang ingin Anda broadcast:")
        bot.register_next_step_handler(msg, process_broadcast)
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

def process_broadcast(message):
    if is_admin(message.from_user.id):
        # Di sini Anda bisa mengirim broadcast ke semua user
        # Untuk contoh, kita hanya menampilkan pesan
        bot.reply_to(message, "📤 Pesan broadcast telah dikirim!")
        logger.log_activity(message.from_user.id, "broadcast_sent")
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

# Handler untuk command /stats
@bot.message_handler(commands=['stats'])
def stats_command(message):
    if is_admin(message.from_user.id):
        db = SessionLocal()
        try:
            stats = get_stats(db)
            stats_text = f"""
📊 Statistik Bot:

👥 Total Pengguna: {stats['total_users']}
✅ Subscription Aktif: {stats['active_subscriptions']}
⚠️ Subscription Kadaluarsa: {stats['expired_subscriptions']}
🆕 Pengguna Baru Hari Ini: {stats['new_users_today']}
💼 Total Seller: {stats['total_sellers']}
            """
            bot.reply_to(message, stats_text)
            logger.log_activity(message.from_user.id, "viewed_stats")
        finally:
            db.close()
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

# Handler untuk menambah seller
@bot.message_handler(commands=['addseller'])
def add_seller_command(message):
    if is_owner(message.from_user.id):
        msg = bot.reply_to(message, "👥 Masukkan ID Telegram user yang ingin dijadikan seller:")
        bot.register_next_step_handler(msg, process_add_seller)
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

def process_add_seller(message):
    if is_owner(message.from_user.id):
        try:
            user_id = int(message.text)
            db = SessionLocal()
            try:
                seller = add_seller(db, user_id, f"Seller {user_id}", message.from_user.id)
                bot.reply_to(message, f"✅ Berhasil menambah seller dengan ID: {user_id}")
                logger.log_activity(message.from_user.id, "added_seller", f"User ID: {user_id}")
                notify_owner(f"🆕 Seller baru ditambahkan: {user_id} oleh {message.from_user.id}")
            finally:
                db.close()
        except ValueError:
            bot.reply_to(message, "❌ Masukkan ID yang valid!")
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

# Handler untuk menghapus seller
@bot.message_handler(commands=['removeseller'])
def remove_seller_command(message):
    if is_owner(message.from_user.id):
        msg = bot.reply_to(message, "👥 Masukkan ID Telegram seller yang ingin dihapus:")
        bot.register_next_step_handler(msg, process_remove_seller)
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

def process_remove_seller(message):
    if is_owner(message.from_user.id):
        try:
            user_id = int(message.text)
            db = SessionLocal()
            try:
                if remove_seller(db, user_id):
                    bot.reply_to(message, f"✅ Berhasil menghapus seller dengan ID: {user_id}")
                    logger.log_activity(message.from_user.id, "removed_seller", f"User ID: {user_id}")
                    notify_owner(f"🗑️ Seller dihapus: {user_id} oleh {message.from_user.id}")
                else:
                    bot.reply_to(message, f"❌ Seller dengan ID {user_id} tidak ditemukan!")
            finally:
                db.close()
        except ValueError:
            bot.reply_to(message, "❌ Masukkan ID yang valid!")
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

# Handler untuk menambah tombol
@bot.message_handler(commands=['addbutton'])
def add_button_command(message):
    if is_owner(message.from_user.id):
        msg = bot.reply_to(message, "🔘 Masukkan detail tombol dalam format:\nNama|Teks|URL|Posisi\n\nContoh: Premium Content|Konten eksklusif|https://example.com|1")
        bot.register_next_step_handler(msg, process_add_button)
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

def process_add_button(message):
    if is_owner(message.from_user.id):
        try:
            parts = message.text.split("|")
            if len(parts) == 4:
                name, text, url, position = parts
                position = int(position)
                
                db = SessionLocal()
                try:
                    button = add_button(db, name, text, url, position)
                    bot.reply_to(message, f"✅ Berhasil menambah tombol: {name}")
                    logger.log_activity(message.from_user.id, "added_button", f"Name: {name}")
                finally:
                    db.close()
            else:
                bot.reply_to(message, "❌ Format tidak valid! Gunakan: Nama|Teks|URL|Posisi")
        except Exception as e:
            bot.reply_to(message, f"❌ Terjadi kesalahan: {str(e)}")
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

# Handler untuk menghapus tombol
@bot.message_handler(commands=['removebutton'])
def remove_button_command(message):
    if is_owner(message.from_user.id):
        msg = bot.reply_to(message, "🔘 Masukkan nama tombol yang ingin dihapus:")
        bot.register_next_step_handler(msg, process_remove_button)
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

def process_remove_button(message):
    if is_owner(message.from_user.id):
        name = message.text
        db = SessionLocal()
        try:
            if remove_button(db, name):
                bot.reply_to(message, f"✅ Berhasil menghapus tombol: {name}")
                logger.log_activity(message.from_user.id, "removed_button", f"Name: {name}")
            else:
                bot.reply_to(message, f"❌ Tombol dengan nama {name} tidak ditemukan!")
        finally:
            db.close()
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

# Handler untuk menambah subscription
@bot.message_handler(commands=['addsubscription'])
def add_subscription_command(message):
    if is_admin(message.from_user.id):
        msg = bot.reply_to(message, "➕ Masukkan ID user dan jumlah hari dalam format:\nID_USER JUMLAH_HARI\n\nContoh: 123456789 30")
        bot.register_next_step_handler(msg, process_add_subscription)
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

def process_add_subscription(message):
    if is_admin(message.from_user.id):
        try:
            parts = message.text.split()
            if len(parts) == 2:
                user_id = int(parts[0])
                days = int(parts[1])
                
                db = SessionLocal()
                try:
                    updated_user = update_subscription(db, user_id, days)
                    if updated_user:
                        log_subscription(db, user_id, message.from_user.id, days)
                        bot.reply_to(message, f"✅ Berhasil menambah {days} hari subscription untuk user {user_id}")
                        logger.log_activity(message.from_user.id, "added_subscription", f"User ID: {user_id}, Days: {days}")
                        notify_owner(f"📥 Subscription ditambahkan: {days} hari untuk user {user_id} oleh {message.from_user.id}")
                    else:
                        bot.reply_to(message, f"❌ Gagal menambah subscription untuk user {user_id}")
                finally:
                    db.close()
            else:
                bot.reply_to(message, "❌ Format tidak valid! Gunakan: ID_USER JUMLAH_HARI")
        except ValueError:
            bot.reply_to(message, "❌ Masukkan ID dan jumlah hari yang valid!")
    else:
        bot.reply_to(message, "❌ Akses ditolak!")

# Handler untuk semua pesan teks
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message):
    db = SessionLocal()
    try:
        user = get_user(db, message.from_user.id)
        if not user:
            user = create_user(
                db, 
                message.from_user.id, 
                message.from_user.username, 
                message.from_user.full_name
            )
        
        # Jika user mengirim pesan dan tidak memiliki akses premium
        if not is_user_premium(message.from_user.id) or not is_user_subscribed(bot, message.from_user.id):
            bot.reply_to(message, "❌ Anda tidak memiliki akses premium untuk mengirim pesan ke bot ini.")
            return
            
        # Di sini Anda bisa menambahkan logika untuk menangani pesan premium
        bot.reply_to(message, "✅ Pesan Anda telah diterima!")
        logger.log_activity(message.from_user.id, "sent_message", message.text[:50])
    finally:
        db.close()

# Handler untuk error
@bot.message_handler(func=lambda message: True)
def handle_errors(message):
    bot.reply_to(message, "❌ Terjadi kesalahan. Silakan coba lagi nanti.")
    logger.log_error(f"Unhandled message from {message.from_user.id}: {message.text}")

# Jalankan bot
if __name__ == "__main__":
    logger.log_system("Bot started")
    notify_owner("🚀 Bot telah dimulai!")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.log_error(f"Bot crashed: {e}")
        notify_owner(f"❌ Bot mengalami kesalahan: {e}")
