import requests
import os


def trigger_spark_job(file_path: str, task_id: str, connection_id: str, account_id: str, service: str, file_type: str, csv_header: str, row_limit:int, col_limit:int, chunksize:int, include_address: bool):
    try:
        payload = {"file_path": file_path, 
                   "task_id": task_id,
                   "connection_id": connection_id,
                   "account_id": account_id,
                   "service": service,
                   "file_type": file_type,
                   "csv_header": csv_header,
                   "row_limit": row_limit,
                   "col_limit": col_limit,
                   "chunksize": chunksize,
                   "include_address": include_address}
        response = requests.post(os.environ.get("SPARK_API_URL"), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to trigger Spark job: {str(e)}")
