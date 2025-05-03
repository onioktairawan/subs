import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from config import API_TOKEN, OWNER_ID, users_collection, logs_collection, CHANNEL_ID

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = "👋 Selamat datang di Bot Premium!\nSilakan pilih menu di bawah ini:"
    keyboard = [
        [InlineKeyboardButton("🛍 Beli Prem Sekarang", callback_data="menu")],
        [InlineKeyboardButton("👤 CS", url="https://t.me/serpagengs")],
        [InlineKeyboardButton("📢 Testimoni", url="https://t.me/testimoniserpa")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


# Menu durasi
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("1 Bulan", callback_data="1_bulan")],
        [InlineKeyboardButton("3 Bulan", callback_data="3_bulan")],
        [InlineKeyboardButton("6 Bulan", callback_data="6_bulan")],
        [InlineKeyboardButton("12 Bulan", callback_data="12_bulan")]
    ]
    await query.edit_message_text("📆 Pilih durasi pembelian:", reply_markup=InlineKeyboardMarkup(keyboard))


# Pilih metode pembayaran
async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    duration = query.data
    context.user_data["durasi"] = duration

    keyboard = [
        [InlineKeyboardButton("QRIS", callback_data='bayar_qris')],
        [InlineKeyboardButton("Bank", callback_data='bayar_bank')],
        [InlineKeyboardButton("DANA", callback_data='bayar_dana')],
        [InlineKeyboardButton("Gopay", callback_data='bayar_gopay')],
        [InlineKeyboardButton("⬅️ Kembali", callback_data='menu')]
    ]
    await query.edit_message_text(
        text=f"Pilih metode pembayaran untuk *{duration.replace('_', ' ')}*:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# Info rekening atau QRIS
async def info_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    metode = query.data.replace("bayar_", "")

    if metode == "qris":
        await query.edit_message_text(
            text="🔗 Silakan scan QRIS atau klik link berikut:\nhttps://t.me/serpagengs"
        )
    else:
        rekening = {
            "bank": ("BCA - 1234567890", "a.n. SERPA GENGS"),
            "dana": ("081234567890", "a.n. SERPA GENGS"),
            "gopay": ("081234567890", "a.n. SERPA GENGS")
        }
        norek, nama = rekening.get(metode, ("-", "-"))
        await query.edit_message_text(
            text=f"""💳 Metode: {metode.upper()}
📛 Nama: {nama}
🏦 Nomor: {norek}

Setelah transfer, silakan kirim bukti (foto) ke bot ini."""
        )


# Terima bukti transfer (foto)
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    file = await update.message.photo[-1].get_file()
    file_path = f'bukti_transfer_{user.id}.jpg'
    await file.download_to_drive(file_path)

    logs_collection.insert_one({
        "user_id": user.id,
        "username": user.username,
        "file_path": file_path,
        "status": "Menunggu konfirmasi"
    })

    await update.message.reply_text("✅ Bukti transfer diterima.\nSelanjutnya, silakan join channel testimoni.")

    try:
        await context.bot.send_message(chat_id=user.id, text="Klik untuk join channel: https://t.me/testimoniserpa")
    except:
        pass


# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


# Main
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(payment_method, pattern="^(1_bulan|3_bulan|6_bulan|12_bulan)$"))
    app.add_handler(CallbackQueryHandler(info_pembayaran, pattern="^bayar_(qris|bank|dana|gopay)$"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_media))
    app.add_error_handler(error_handler)

    app.run_polling()


if __name__ == '__main__':
    main()
