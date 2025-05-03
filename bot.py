import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client["business_bot"]
users_collection = db["users"]
logs_collection = db["logs"]

# Ganti dengan token bot Telegram Anda dari .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Fungsi untuk log pesan
def log_message(user_id, message):
    logs_collection.insert_one({
        "user_id": user_id,
        "message": message,
        "timestamp": datetime.datetime.now()
    })

# Fungsi untuk menampilkan log (hanya untuk owner)
def get_log(update, context):
    if update.message.chat_id == OWNER_ID:
        logs = logs_collection.find()
        log_text = "\n".join([f"User {log['user_id']}: {log['message']}" for log in logs])
        update.message.reply_text(log_text)
    else:
        update.message.reply_text("You are not authorized to view the logs.")

# Konstanta untuk step conversation
SELECT_DURATION, SELECT_PAYMENT_METHOD = range(2)

# Fungsi untuk tombol /start
def start(update, context):
    keyboard = [
        [InlineKeyboardButton("Beli Prem Sekarang", callback_data='buy_prem')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Selamat datang! Tekan tombol di bawah untuk memulai.', reply_markup=reply_markup)

# Fungsi untuk memulai pembelian
def buy_prem(update, context):
    keyboard = [
        [InlineKeyboardButton("1 Bulan", callback_data='1')],
        [InlineKeyboardButton("3 Bulan", callback_data='3')],
        [InlineKeyboardButton("6 Bulan", callback_data='6')],
        [InlineKeyboardButton("12 Bulan", callback_data='12')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Berapa bulan yang ingin Anda beli?", reply_markup=reply_markup)
    return SELECT_DURATION

# Fungsi untuk memilih durasi
def select_duration(update, context):
    query = update.callback_query
    context.user_data['duration'] = query.data  # Simpan durasi yang dipilih
    query.edit_message_text(text=f"Durasi {query.data} bulan dipilih. Sekarang pilih metode pembayaran.")
    
    keyboard = [
        [InlineKeyboardButton("QRIS", callback_data='qris')],
        [InlineKeyboardButton("Bank", callback_data='bank')],
        [InlineKeyboardButton("DANA", callback_data='dana')],
        [InlineKeyboardButton("Gopay", callback_data='gopay')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text("Pilih metode pembayaran:", reply_markup=reply_markup)
    return SELECT_PAYMENT_METHOD

# Fungsi untuk memilih metode pembayaran
def select_payment_method(update, context):
    query = update.callback_query
    method = query.data
    duration = context.user_data.get('duration')

    payment_info = {
        "qris": f"Nomor Rekening: 12345\nNama Penerima: John Doe\nQRIS Link: example.com/qris (Durasi: {duration} bulan)",
        "bank": f"Nomor Rekening: 12345\nNama Penerima: John Doe (Durasi: {duration} bulan)",
        "dana": f"Nomor Rekening: 12345\nNama Penerima: John Doe\nDANA Link: example.com/dana (Durasi: {duration} bulan)",
        "gopay": f"Nomor Rekening: 12345\nNama Penerima: John Doe\nGopay Link: example.com/gopay (Durasi: {duration} bulan)"
    }
    
    query.edit_message_text(text=payment_info[method])
    query.message.reply_text("Silakan kirim bukti transfer Anda untuk melanjutkan.")
    return ConversationHandler.END

# Fungsi untuk menangani pengiriman bukti transfer
def handle_media(update, context):
    user_id = update.message.from_user.id
    if update.message.photo or update.message.document:
        log_message(user_id, "Bukti transfer diterima.")
        update.message.reply_text("Terima kasih! Silakan subscribe ke channel testimoni.")
        # Lakukan force subscribe ke channel testimoni
        # (Logika force subscribe akan ditambahkan nanti)
    else:
        update.message.reply_text("Harap kirim bukti transfer dalam bentuk foto atau file.")

# Fungsi utama untuk menjalankan bot
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # ConversationHandler untuk alur pembelian
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(buy_prem, pattern='^buy_prem$')],
        states={
            SELECT_DURATION: [CallbackQueryHandler(select_duration)],
            SELECT_PAYMENT_METHOD: [CallbackQueryHandler(select_payment_method)],
        },
        fallbacks=[],
    )

    # Handlers
    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.photo | Filters.document, handle_media))
    dp.add_handler(CommandHandler("log", get_log))  # Hanya untuk owner

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
