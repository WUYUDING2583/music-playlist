from app.netease.main import Netease
import asyncio


async def main():
    netease = Netease("yun.cookie.txt")
    await netease.download_song([447925059])


if __name__ == "__main__":
    # playlist_id = 919939187
    # song_id = 447925059
    # netease = Netease("yun.cookie.txt")
    # netease.export_song_lyric_srt_file(song_id)
    # netease.get_playlist(playlist_id)
    asyncio.run(main())

#  yun 919939187 -f ':name/:singer - :songName.mp3' --cookie
