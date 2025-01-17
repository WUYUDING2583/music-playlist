import os
from dotenv import load_dotenv

load_dotenv(override=True)

mongo_db_host = os.getenv("MONGO_DB_HOST")

minio_access_key = os.getenv("MINIO_ACCESS_KEY")
minio_secret_key = os.getenv("MINIO_SECRET_KEY")
minio_endpoint = os.getenv("MINIO_ENDPOINT")
