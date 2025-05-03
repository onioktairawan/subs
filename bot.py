import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from config import OWNER_ID, MONGO_URI, CHANNEL_ID, BOT_TOKEN, API_ID, API_HASH

# Koneksi MongoDB
client = MongoClient(MONGO_URI)
db = client["teleprem"]
transactions_collection = db["transactions"]
users_collection = db["users"]

# Inisialisasi bot dengan Pyrogram
app = Client("teleprem_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Fungsi untuk mengirim pesan ke Owner
async def send_to_owner(message):
    await app.send_message(OWNER_ID, message)

# Fungsi untuk mengambil data pengguna dari MongoDB
def get_user(user_id):
    return users_collection.find_one({"user_id": user_id})

# Fungsi untuk memperbarui data pengguna di MongoDB
def update_user(user_id, update_data):
    users_collection.update_one({"user_id": user_id}, {"$set": update_data})

# Fungsi untuk menambahkan transaksi baru
def create_transaction(user_id, amount):
    transactions_collection.insert_one({
        "user_id": user_id,
        "amount": amount,
        "status": "pending"
    })

# Handle /start command
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"

    # Cek apakah user sudah terdaftar
    user = get_user(user_id)
    if not user:
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "step": "awaiting_payment"
        })

    # Kirim pesan dengan tombol inline
    await message.reply(
        "Selamat datang! Pilih menu di bawah:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menu", callback_data="menu")],
            [InlineKeyboardButton("CS", callback_data="cs")],
            [InlineKeyboardButton("Testimoni", callback_data="testimoni")]
        ])
    )

# Handle tombol menu
@app.on_callback_query(filters.regex("menu"))
async def menu(client, query):
    await query.answer()
    await query.message.edit(
        "Pilih durasi pembelian:\n1. 1 bulan\n2. 3 bulan\n3. 6 bulan\n4. 12 bulan",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Bulan", callback_data="buy_1_month")],
            [InlineKeyboardButton("3 Bulan", callback_data="buy_3_months")],
            [InlineKeyboardButton("6 Bulan", callback_data="buy_6_months")],
            [InlineKeyboardButton("12 Bulan", callback_data="buy_12_months")]
        ])
    )

# Handle pemilihan durasi pembelian
@app.on_callback_query(filters.regex("buy_"))
async def buy_duration(client, query):
    duration = query.data.split("_")[-1]
    user_id = query.from_user.id
    user = get_user(user_id)

    # Simpan transaksi ke MongoDB dengan status pending
    create_transaction(user_id, duration)

    await query.answer("Silakan kirim bukti transfer sebagai media.")

# Handle bukti transfer
@app.on_message(filters.media)
async def handle_transfer(client, message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if user and user['step'] == 'awaiting_payment':
        # Simpan bukti transfer dan update status transaksi
        transaction = transactions_collection.find_one({"user_id": user_id, "status": "pending"})
        transactions_collection.update_one({"_id": transaction["_id"]}, {"$set": {"status": "awaiting_confirmation"}})

        # Kirim notifikasi ke owner
        transaction_details = f"""
        Transaksi baru dari User @{user['username']}:
        - Durasi Pembelian: {transaction['amount']}
        - Pembayaran: Bukti Transfer Diterima
        """
        await send_to_owner(transaction_details)

        await message.reply("Bukti transfer diterima, menunggu konfirmasi dari owner.")

# Handle konfirmasi pembayaran dari Owner
@app.on_callback_query(filters.regex("confirm_payment"))
async def confirm_payment(client, query):
    user_id = query.from_user.id
    user = get_user(user_id)

    if user and user['step'] == 'awaiting_confirmation':
        # Update status transaksi dan user
        transaction = transactions_collection.find_one({"user_id": user_id, "status": "awaiting_confirmation"})
        transactions_collection.update_one({"_id": transaction["_id"]}, {"$set": {"status": "confirmed"}})

        update_user(user_id, {"step": "awaiting_phone_number"})

        await query.answer("Pembayaran telah dikonfirmasi. Lanjutkan ke proses berikutnya.")

# Handle button lainnya seperti CS, Testimoni
@app.on_callback_query(filters.regex("cs"))
async def cs(client, query):
    await query.answer()
    await query.message.edit("Anda dapat menghubungi Owner di sini!")

@app.on_callback_query(filters.regex("testimoni"))
async def testimoni(client, query):
    await query.answer()
    await query.message.edit("Silakan kunjungi Channel Testimoni kami!")
    await app.send_message(CHANNEL_ID, "Terima kasih telah bergabung di channel testimoni kami!")

if __name__ == "__main__":
    app.run()
