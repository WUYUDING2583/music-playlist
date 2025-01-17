from .client import song_collection


def insert_song(song: dict):
    song_collection.create_index("id", unique=True)
    return song_collection.insert_one(song)


def insert_songs(songs: list[dict]):
    song_collection.create_index("id", unique=True)
    return song_collection.insert_many(songs)


def get_song(song_id: str):
    song = song_collection.find_one({"id": song_id})
    if song:
        song.pop("_id")
        return song
    else:
        return None


def update_song(song: dict):
    return song_collection.update_one({"id": song["id"]}, {"$set": song})
