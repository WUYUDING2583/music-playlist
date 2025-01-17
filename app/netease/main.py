import os
import sys

import requests
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.netease.netease_api import NeteaseApi
from app.mongodb.playlist import get_playlist as get_playlist_from_db, insert_playlist
from app.mongodb.song import insert_songs, get_song as get_song_from_db, update_song
from app.utils.log import logger
from app.min_io.services import upload_file, presign_download, file_exists
from app.min_io.client import BucketName


class Netease:
    def __init__(self, cookie_file: str):
        self.netease_api = NeteaseApi(cookie_file)

    async def download_song(
        self, song_ids: list, download_directory="music", quality: str = "lossless"
    ):
        logger.info(f"Downloading songs {song_ids} with quality {quality}")
        missing_song_ids = []
        songs_url = []
        # Get song url from minio
        for song_id in song_ids:
            if file_exists(f"{song_id}.mp3", BucketName.MUSIC_PLAYLIST.value):
                song_url = presign_download(
                    f"{song_id}.mp3", BucketName.MUSIC_PLAYLIST.value
                )
                print(song_url)
                songs_url.append({"id": song_id, "url": song_url, "is_minio": True})
            else:
                missing_song_ids.append(song_id)
        logger.info(f"Got {len(songs_url)} songs url from minio")
        # If missing song ids, get song url from netease api
        if len(missing_song_ids) > 0:
            logger.info(f"Getting {len(missing_song_ids)} songs url from netease api")
            songs_url.extend(self.get_songs_url(missing_song_ids, quality))
            logger.info(f"Got {len(songs_url)} songs url from netease api")

        for song_url in songs_url:
            if not song_url["url"]:
                logger.error(f"No url found for song {song['id']}")
                continue
            song_id = song_url["id"]
            song = self.get_song(song_id)
            logger.info(f"Downloading song {song['name']} ID:{song['id']}")
            # Create music directory if it doesn't exist
            music_dir = Path(download_directory)
            music_dir.mkdir(exist_ok=True)

            # Download the song
            response = requests.get(song_url["url"], stream=True)
            if response.status_code == 200:
                # Use song id as filename since we don't have song name info here
                filename = music_dir / f"{song['id']}.mp3"

                logger.info(f"Downloading to {filename}...")
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                if not song_url["is_minio"]:
                    await upload_file(
                        f"{song['id']}.mp3", filename, BucketName.MUSIC_PLAYLIST.value
                    )
                logger.info(f"Download complete!")

    def get_songs_url(self, song_ids: list, quality: str = "lossless"):
        logger.info(f"Getting songs url for {song_ids} with quality {quality}")
        urls = self.netease_api.get_songs_url_with_quality(song_ids, quality)
        logger.info(f"Got {len(urls)} songs url")
        return urls

    def get_playlist(self, playlist_id: int):
        logger.info(f"Getting playlist {playlist_id} from db")
        playlist = get_playlist_from_db(playlist_id)
        if playlist:
            logger.info(f"Playlist {playlist['name']} ID:{playlist_id} found in db")
            playlist = self.get_playlist_songs(playlist)
            return playlist
        # no playlist in mongodb, get playlist from netease api
        logger.info(f"Playlist {playlist_id} not found in db, getting from netease api")
        playlist_name, playlist_description, track_ids = self.netease_api.get_playlist(
            playlist_id
        )
        playlist = {
            "id": playlist_id,
            "name": playlist_name,
            "description": playlist_description,
            "track_ids": track_ids,
        }
        insert_playlist(playlist)
        logger.info(f"Playlist {playlist['name']} ID:{playlist_id} inserted into db")
        playlist = self.get_playlist_songs(playlist)
        return playlist

    def get_playlist_songs(self, playlist: dict):
        logger.info(
            f"Getting songs for playlist {playlist['name']} ID:{playlist['id']}"
        )
        track_ids = playlist["track_ids"]
        tracks = []
        missing_track_ids = []
        missing_tracks = []
        for track_id in track_ids:
            # get song from mongodb
            song = get_song_from_db(track_id)
            if song:
                logger.info(f"Song {song['name']} ID:{song['id']} found in db")
                tracks.append(song)
            else:
                logger.info(
                    f"Song {track_id} not found in db, getting from netease api"
                )
                missing_track_ids.append(track_id)
        # if missing track ids, get songs from netease api
        if len(missing_track_ids) > 0:
            logger.info(f"Getting {len(missing_track_ids)} songs from netease api")
            songs_data = self.netease_api.get_songs(missing_track_ids)
            for song in songs_data:
                missing_tracks.append(
                    {
                        "id": song.get("id", ""),
                        "name": song.get("name", ""),
                        "singer": song.get("ar", [{}])[0],
                        "album": song.get("al", {}),
                    }
                )
            # insert missing songs to mongodb
            insert_songs(missing_tracks)
            logger.info(f"Inserted {len(missing_tracks)} songs to db")
            tracks.extend(missing_tracks)
        playlist["tracks"] = tracks
        return playlist

    def get_lyric(self, song_id):
        """Get lyric from db, if no lyric in db
        then get lyric from netease api and upload to db"""
        logger.info(f"Getting lyric for song {song_id}")
        song = self.get_song(song_id)
        if song:
            lyric = song.get("lyric", "")
            if lyric:
                logger.info(
                    f"Lyric for song {song['name']} ID:{song['id']} found in db"
                )
                return lyric, song
        logger.info(
            f"Lyric for song {song['name']} ID:{song['id']} not found in db, getting from netease api"
        )
        lyric = self.netease_api.get_lyric(song_id)
        logger.info(
            f"Lyric for song {song['name']} ID:{song['id']} got from netease api"
        )
        song["lyric"] = lyric
        update_song(song)
        logger.info(f"Lyric for song {song['name']} ID:{song['id']} inserted into db")
        return lyric, song

    def get_song(self, song_id):
        logger.info(f"Getting song {song_id} from db")
        song = get_song_from_db(song_id)
        if song:
            logger.info(f"Song {song['name']} ID:{song['id']} found in db")
            return song
        logger.info(f"Song {song_id} not found in db, getting from netease api")
        songs_data = self.netease_api.get_songs([song_id])
        songs = []
        for song in songs_data:
            logger.info(f"Song {song['name']} ID:{song['id']} got from netease api")
            songs.append(
                {
                    "id": song.get("id", ""),
                    "name": song.get("name", ""),
                    "singer": song.get("ar", [{}])[0],
                    "album": song.get("al", {}),
                }
            )
        insert_songs(songs)
        logger.info(f"Inserted {songs[0]['name']} ID:{songs[0]['id']} to db")
        return songs[0]

    def export_song_lyric_srt_file(self, song_id):
        logger.info(f"Exporting lyric for song {song_id}")
        lyric, song = self.get_lyric(song_id)
        if not lyric:
            logger.error(f"No lyric found for song {song_id}")
            return False

        filename = f"{song['name']} - {song['singer']['name']}.srt"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                lines = lyric.split("\n")
                counter = 1

                for i in range(0, len(lines), 2):
                    if i + 1 >= len(lines):
                        break

                    time_line = lines[i]
                    if not time_line.startswith("["):
                        continue

                    # Extract timestamp
                    time_str = time_line[1 : time_line.find("]")]
                    try:
                        minutes, seconds = time_str.split(":")
                        start_time = f"00:{minutes}:{seconds},000"

                        # Calculate end time (assume 3 seconds duration)
                        min_val = int(minutes)
                        sec_val = float(seconds) + 3
                        if sec_val >= 60:
                            sec_val -= 60
                            min_val += 1
                        end_time = f"00:{min_val:02d}:{sec_val:06.3f}".replace(".", ",")

                        # Write SRT entry
                        f.write(f"{counter}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{lines[i + 1]}\n\n")
                        counter += 1

                    except ValueError:
                        continue

            logger.info(f"Successfully exported lyric to SRT file: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to create SRT file: {e}")
            return False
