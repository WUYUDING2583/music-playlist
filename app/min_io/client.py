from minio import Minio
from minio.error import S3Error
from enum import Enum
from constants.env import (
    minio_access_key,
    minio_secret_key,
    minio_endpoint,
)

minio_client = Minio(
    endpoint=minio_endpoint,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=False,
)


class BucketName(Enum):
    MUSIC_PLAYLIST = "music-playlist"


# Loop through bucket names and create if they don't exist
for bucket in BucketName:
    found = minio_client.bucket_exists(bucket.value)
    if not found:
        minio_client.make_bucket(bucket.value)
