from pymongo import MongoClient
from app.constants.env import mongo_db_host

# Connect to MongoDB
client = MongoClient(mongo_db_host)

# Access a specific database and collection
db = client["music-playlist"]

playlist_collection = db["playlist"]
song_collection = db["song"]
