import requests
import json
from pathlib import Path
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.netease.prepare_request import prepare_request
from app.utils.log import logger

# Different quality levels
quality_levels = {
    "standard": {"level": "standard", "br": 320000},
    "high": {"level": "exhigh", "br": 320000},
    "lossless": {"level": "lossless", "br": 999000},
    "hires": {"level": "hires", "br": 999000},
}


class NeteaseApi:
    def __init__(self, cookie_file: str):
        self.cookie_content = self.read_cookie(cookie_file)

        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://music.163.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Origin": "https://music.163.com",
            "Cookie": self.cookie_content,
        }

    def get_playlist(self, playlist_id: str):
        url = "https://music.163.com/weapi/v6/playlist/detail?csrf_token="
        playlist_data = {
            "csrf_token": "",
            "id": playlist_id,
            "offset": 0,
            "total": True,
            "limit": 1000,
            "withSongs": True,
            "n": 1000,
        }
        encrypted = prepare_request(playlist_data)
        response = requests.post(url, data=encrypted, headers=self.headers)
        playlist = response.json().get("playlist", {})
        playlist_name = playlist.get("name", "")
        playlist_description = playlist.get("description", "")
        track_ids = [i["id"] for i in playlist.get("trackIds", [])]

        return playlist_name, playlist_description, track_ids

    def get_songs(self, song_ids: list[str]):
        """
        Get details for multiple songs by their IDs
        Args:
            song_ids (list): List of song IDs
        Returns:
            dict: The response containing songs information
        """
        url = "https://music.163.com/weapi/v3/song/detail?csrf_token="

        # Format the song IDs into the required structure
        c = []
        for id in song_ids:
            c.append({"id": id})

        data = {
            "c": json.dumps(c),  # Convert the list to JSON string
            "ids": json.dumps(song_ids),  # Convert the IDs list to JSON string
            "csrf_token": "",
        }

        encrypted = prepare_request(data)
        response = requests.post(url, data=encrypted, headers=self.headers)
        return response.json().get("songs", [])

    def get_lyric(self, song_id):
        url = "https://music.163.com/weapi/song/lyric?csrf_token="

        data = {
            "id": song_id,
            "os": "pc",
            "lv": "-1",
            "kv": "-1",
            "tv": "-1",
            "csrf_token": "",
        }

        encrypted = prepare_request(data)

        response = requests.post(url, data=encrypted, headers=self.headers)
        return response.json().get("lrc", {}).get("lyric", "")

    def convert_timestamp(self, lrc_time):
        """Convert [mm:ss.ms] to SRT format HH:MM:SS,mmm"""
        # Remove brackets
        time_str = lrc_time[1:-1]

        # Split minutes and seconds
        minutes, seconds = time_str.split(":")

        # Convert to integers/float
        minutes = int(minutes)
        seconds = float(seconds)

        # Calculate hours, minutes, seconds, milliseconds
        hours = minutes // 60
        minutes = minutes % 60
        whole_seconds = int(seconds)
        milliseconds = int((seconds - whole_seconds) * 1000)

        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"

    def lrc_to_srt(self, lrc_text):
        # Split into lines and filter empty lines
        lines = [line for line in lrc_text.split("\n") if line.strip()]

        srt_lines = []
        counter = 1

        for i, line in enumerate(lines):
            # Skip lines without proper timestamp
            if not line.startswith("[") or "]" not in line:
                continue

            # Extract timestamp and text
            timestamp = line[:10]  # Get [mm:ss.mmm]
            text = line[11:].strip()

            # Convert current timestamp
            start_time = self.convert_timestamp(timestamp)

            # Get end time from next line or add 5 seconds if it's the last line
            if i + 1 < len(lines) and lines[i + 1].startswith("["):
                end_timestamp = lines[i + 1][:10]
                end_time = self.convert_timestamp(end_timestamp)
            else:
                # For the last line, add 5 seconds
                hours, minutes, rest = start_time.split(":")
                seconds, ms = rest.split(",")
                # Convert string to int for minutes and seconds
                minutes = int(minutes)
                new_seconds = int(seconds) + 5
                if new_seconds >= 60:
                    minutes = minutes + (new_seconds // 60)
                    new_seconds = new_seconds % 60
                end_time = f"{hours}:{minutes:02d}:{new_seconds:02d},{ms}"

            # Create SRT entry
            srt_entry = f"{counter}\n{start_time} --> {end_time}\n{text}\n"
            srt_lines.append(srt_entry)
            counter += 1

        return "\n".join(srt_lines)

    def read_cookie(self, cookie_file: str) -> None:
        """
        Read and process cookie file content, storing it in COOKIE_CONTENT global variable.

        Args:
            cookie_file (str): Path to the cookie file
        """

        if not cookie_file:
            return

        file_path = Path(cookie_file).resolve()
        if not file_path.exists():
            logger.warning(f"[cookie] cookie file does not exist: {file_path}")
            return
        else:
            logger.info(f"[cookie] using cookie file: {file_path}")

        # Read file and process content
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Remove comments and empty lines
        processed_content = "".join(
            line for line in lines if line.strip() and not line.strip().startswith("//")
        )

        return processed_content

    # Example: Get high quality URLs
    def get_songs_url_with_quality(self, song_ids, quality="lossless"):
        url = "https://music.163.com/weapi/song/enhance/player/url/v1?csrf_token="

        quality_params = quality_levels.get(quality, quality_levels["lossless"])

        data = {
            "ids": song_ids,
            "level": quality_params["level"],
            "encodeType": "aac",
            "csrf_token": "",
            "br": quality_params["br"],
        }

        encrypted = prepare_request(data)
        response = requests.post(url, data=encrypted, headers=self.headers)
        return response.json().get("data", [])
