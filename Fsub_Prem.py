import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# --- Konfigurasi ---
# Ganti dengan token bot Anda dari BotFather
TOKEN = "YOUR_BOT_TOKEN"

# Ganti dengan username channel premium Anda, contoh: "premium_channel" (tanpa @)
CHANNEL_USERNAME = "nama_channel_premium_anda"

# Ganti dengan ID admin (pemilik bot) yang Anda dapatkan dari @userinfobot
ADMIN_ID = YOUR_ADMIN_ID

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Fungsi-Fungsi Bot ---

# Fungsi untuk memeriksa status keanggotaan pengguna di channel
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat_member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Gagal memeriksa keanggotaan untuk user {user_id}: {e}")
        return False

# Perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Inisialisasi set untuk menyimpan user premium jika belum ada
    if 'premium_users' not in context.bot_data:
        context.bot_data['premium_users'] = set()

    if user_id in context.bot_data['premium_users']:
        # Jika pengguna premium, kirim tombol untuk masuk channel
        keyboard = [[InlineKeyboardButton("Masuk Channel Premium", url=f"https://t.me/{CHANNEL_USERNAME}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Selamat datang, pelanggan premium! Anda bisa mengakses channel sekarang:",
            reply_markup=reply_markup
        )
    else:
        # Jika bukan premium, kirim tombol untuk membeli langganan
        keyboard = [[InlineKeyboardButton("Beli Langganan", callback_data="buy_premium")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Halo! Silakan beli langganan untuk mendapatkan akses ke channel premium.",
            reply_markup=reply_markup
        )

# Callback untuk tombol "Beli Langganan"
async def buy_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    # Pesan ini bisa disesuaikan dengan instruksi pembayaran
    await query.edit_message_text(
        text="Silakan lakukan pembayaran untuk langganan. Setelah itu, beritahu admin agar akses Anda diaktifkan."
    )

# --- Perintah Admin (khusus untuk pemilik bot) ---

# Perintah untuk menambahkan user ke daftar premium
async def add_premium_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Maaf, perintah ini hanya untuk admin.")
        return

    try:
        user_id_to_add = int(context.args[0])
        if user_id_to_add not in context.bot_data['premium_users']:
            context.bot_data['premium_users'].add(user_id_to_add)
            await update.message.reply_text(f"Pengguna dengan ID {user_id_to_add} telah ditambahkan ke daftar premium.")
        else:
            await update.message.reply_text(f"Pengguna dengan ID {user_id_to_add} sudah ada di daftar premium.")
    except (IndexError, ValueError):
        await update.message.reply_text("Penggunaan: /add_premium_user <user_id>")

# Perintah untuk menghapus user dari daftar premium
async def remove_premium_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Maaf, perintah ini hanya untuk admin.")
        return

    try:
        user_id_to_remove = int(context.args[0])
        if user_id_to_remove in context.bot_data['premium_users']:
            context.bot_data['premium_users'].remove(user_id_to_remove)
            await update.message.reply_text(f"Pengguna dengan ID {user_id_to_remove} telah dihapus dari daftar premium.")
        else:
            await update.message.reply_text(f"Pengguna dengan ID {user_id_to_remove} tidak ada di daftar premium.")
    except (IndexError, ValueError):
        await update.message.reply_text("Penggunaan: /remove_premium_user <user_id>")

# Perintah untuk menampilkan daftar user premium
async def list_premium_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Maaf, perintah ini hanya untuk admin.")
        return

    premium_users = context.bot_data.get('premium_users', set())
    if premium_users:
        user_list = "\n".join(str(user_id) for user_id in premium_users)
        await update.message.reply_text(f"Daftar Pengguna Premium:\n{user_list}")
    else:
        await update.message.reply_text("Belum ada pengguna premium.")

def main() -> None:
    """Menjalankan bot."""
    application = Application.builder().token(TOKEN).build()
    
    # Menyimpan daftar user premium dalam memory bot
    application.bot_data['premium_users'] = set()

    # Menambahkan handler untuk perintah
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_premium_user", add_premium_user))
    application.add_handler(CommandHandler("remove_premium_user", remove_premium_user))
    application.add_handler(CommandHandler("list_premium_users", list_premium_users))
    
    # Menambahkan handler untuk tombol callback
    application.add_handler(CallbackQueryHandler(buy_premium_callback, pattern="^buy_premium$"))

    # Menjalankan bot sampai menekan Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()