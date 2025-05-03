import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
from pymongo import MongoClient
from config import API_TOKEN, OWNER_ID, users_collection, logs_collection, CHANNEL_ID

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Start command
def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    welcome_text = "Selamat datang! Silakan pilih menu."
    
    keyboard = [
        [InlineKeyboardButton("Menu", callback_data='menu')],
        [InlineKeyboardButton("CS", callback_data='cs')],
        [InlineKeyboardButton("Testimoni", callback_data='testimoni')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Menu button handler
def menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("1 Bulan", callback_data='1_bulan')],
        [InlineKeyboardButton("3 Bulan", callback_data='3_bulan')],
        [InlineKeyboardButton("6 Bulan", callback_data='6_bulan')],
        [InlineKeyboardButton("12 Bulan", callback_data='12_bulan')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(text="Pilih durasi pembelian:", reply_markup=reply_markup)

# Payment method handler
def payment_method(update: Update, context: CallbackContext) -> None:
    duration = update.callback_query.data
    keyboard = [
        [InlineKeyboardButton("QRIS", callback_data='qris')],
        [InlineKeyboardButton("Bank", callback_data='bank')],
        [InlineKeyboardButton("DANA", callback_data='dana')],
        [InlineKeyboardButton("Gopay", callback_data='gopay')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.callback_query.edit_message_text(text=f"Pilih metode pembayaran untuk {duration}:", reply_markup=reply_markup)

# Handle media transfer (bukti transfer)
def handle_media(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    file = update.message.photo[-1].get_file()
    file.download(f'bukti_transfer_{user_id}.jpg')
    
    # Log the payment evidence
    logs_collection.insert_one({
        "user_id": user_id,
        "file_path": f'bukti_transfer_{user_id}.jpg',
        "status": "Payment awaiting confirmation"
    })
    
    update.message.reply_text("Bukti transfer diterima. Menunggu konfirmasi pembayaran...")

# Confirm payment
def confirm_payment(update: Update, context: CallbackContext) -> None:
    user_id = update.callback_query.from_user.id
    
    # Log confirmation
    logs_collection.update_one(
        {"user_id": user_id, "status": "Payment awaiting confirmation"},
        {"$set": {"status": "Payment confirmed"}}
    )
    
    update.callback_query.edit_message_text(text="Pembayaran terkonfirmasi. Silakan lanjutkan ke pengisian nomor HP.")

# Force Subscribe to Testimoni Channel
def force_subscribe(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    
    # Force subscribe to testimonial channel
    context.bot.get_chat_member(CHANNEL_ID, user_id)
    
    update.message.reply_text("Anda telah bergabung dengan channel testimoni.")

# Error handler
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    updater = Updater(API_TOKEN)

    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(menu, pattern='^menu$'))
    dp.add_handler(CallbackQueryHandler(payment_method, pattern='^(1_bulan|3_bulan|6_bulan|12_bulan)$'))
    dp.add_handler(CallbackQueryHandler(confirm_payment, pattern='^confirm_payment$'))

    # Media handler
    dp.add_handler(MessageHandler(Filters.photo, handle_media))

    # Error handler
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
