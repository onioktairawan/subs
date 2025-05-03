import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from config import API_TOKEN, OWNER_ID, users_collection, logs_collection, CHANNEL_ID

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_text = "Selamat datang! Silakan pilih menu."

    keyboard = [
        [InlineKeyboardButton("Menu", callback_data='menu')],
        [InlineKeyboardButton("CS", callback_data='cs')],
        [InlineKeyboardButton("Testimoni", callback_data='testimoni')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Menu pilihan durasi
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("1 Bulan", callback_data='1_bulan')],
        [InlineKeyboardButton("3 Bulan", callback_data='3_bulan')],
        [InlineKeyboardButton("6 Bulan", callback_data='6_bulan')],
        [InlineKeyboardButton("12 Bulan", callback_data='12_bulan')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Pilih durasi pembelian:", reply_markup=reply_markup)

# Metode pembayaran
async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    duration = update.callback_query.data
    keyboard = [
        [InlineKeyboardButton("QRIS", callback_data='qris')],
        [InlineKeyboardButton("Bank", callback_data='bank')],
        [InlineKeyboardButton("DANA", callback_data='dana')],
        [InlineKeyboardButton("Gopay", callback_data='gopay')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(
        f"Pilih metode pembayaran untuk {duration}:", reply_markup=reply_markup
    )

# Upload bukti transfer
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    file = await update.message.photo[-1].get_file()
    path = f'bukti_transfer_{user_id}.jpg'
    await file.download_to_drive(path)

    logs_collection.insert_one({
        "user_id": user_id,
        "file_path": path,
        "status": "Payment awaiting confirmation"
    })

    await update.message.reply_text("Bukti transfer diterima. Menunggu konfirmasi pembayaran...")

# Konfirmasi pembayaran
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id

    logs_collection.update_one(
        {"user_id": user_id, "status": "Payment awaiting confirmation"},
        {"$set": {"status": "Payment confirmed"}}
    )

    await update.callback_query.edit_message_text(
        "Pembayaran terkonfirmasi. Silakan lanjutkan ke pengisian nomor HP."
    )

# Force Subscribe ke channel testimoni
async def force_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    try:
        await context.bot.get_chat_member(CHANNEL_ID, user_id)
        await update.message.reply_text("Anda telah bergabung dengan channel testimoni.")
    except:
        await update.message.reply_text("Silakan join channel testimoni dulu untuk melanjutkan.")

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

# Main app
def main():
    app = Application.builder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(payment_method, pattern="^(1_bulan|3_bulan|6_bulan|12_bulan)$"))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_payment$"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_media))

    app.add_error_handler(error_handler)

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
