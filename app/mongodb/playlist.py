from .client import playlist_collection
from pymongo.results import InsertOneResult, UpdateResult


def insert_playlist(playlist: dict) -> InsertOneResult:
    playlist_collection.create_index("id", unique=True)
    return playlist_collection.insert_one(playlist)


def get_playlist(id: str):
    playlist = playlist_collection.find_one({"id": id})
    if playlist:
        playlist.pop("_id")
        return playlist
    else:
        return None


def update_playlist(playlist: dict) -> UpdateResult:
    return playlist_collection.update_one({"id": playlist["id"]}, {"$set": playlist})
