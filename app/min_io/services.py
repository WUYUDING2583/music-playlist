from minio.error import S3Error
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from min_io.client import minio_client, BucketName
from utils.log import logger


async def upload_file(
    file_name: str,
    file_path: str,
    bucket_name: str = BucketName.MUSIC_PLAYLIST.value,
):
    if not os.path.isfile(file_path):
        logger.error(f"Error: The file {file_path} does not exist.")
        return False

    # Ensure bucket exists
    if not minio_client.bucket_exists(bucket_name):
        logger.error(f"Bucket {bucket_name} does not exist.")
        return False

    # Get the file size
    file_stat = os.stat(file_path)
    file_size = file_stat.st_size

    # Open the file in binary mode
    with open(file_path, "rb") as file_data:
        try:
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=file_name,
                data=file_data,
                length=file_size,
                content_type="application/octet-stream",
            )
            logger.info(
                f"File {file_path} uploaded successfully as {file_name} in bucket {bucket_name}."
            )
            return True
        except S3Error as e:
            logger.error(f"Failed to upload {file_path} to MinIO: {e}")
            return False


def presign_upload(filename: str, bucket_name: str = BucketName.MUSIC_PLAYLIST.value):
    url = minio_client.presigned_put_object(bucket_name, filename)
    return url


def presign_download(filename: str, bucket_name: str = BucketName.MUSIC_PLAYLIST.value):
    try:
        url = minio_client.presigned_get_object(bucket_name, filename)

        return url
    except S3Error:
        return None


def file_exists(
    filename: str, bucket_name: str = BucketName.MUSIC_PLAYLIST.value
) -> bool:
    try:
        minio_client.stat_object(bucket_name, filename)
        return True
    except S3Error:
        return False
