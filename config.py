import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Telegram bot token
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.get_database()

# Collection references
users_collection = db.users
logs_collection = db.logs

# Owner info
OWNER_ID = os.getenv("OWNER_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
