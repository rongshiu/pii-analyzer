from minio import Minio
import os

client = Minio(os.environ.get("MINIO_ENDPOINT"), access_key=os.environ.get("MINIO_ACCESS_KEY"), secret_key=os.environ.get("MINIO_SECRET_KEY"), secure=False)

def download_from_minio(file_path, download_dir="/tmp"):
    bucket, *key = file_path.split("/", 1)
    key = key[0]
    local_file = os.path.join(download_dir, os.path.basename(key))
    client.fget_object(bucket, key, local_file)
    return local_file
