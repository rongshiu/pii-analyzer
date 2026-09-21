# app/v1/api.py
import os
import asyncio
from datetime import datetime

from utility.logger import get_logger

from fastapi import APIRouter, HTTPException
from schema.api_schema import SparkJob
from celery_worker import celery_app

logger = get_logger()
router = APIRouter()

API_VERSION = "v1"
env = os.environ.get("HOST_ENV", "development")
CELERY_SPARK_QUEUE = os.getenv("CELERY_SPARK_QUEUE", "spark")

@router.post(f"/{API_VERSION}/trigger-job")
async def trigger_job(request: SparkJob):
    try:
        result = celery_app.send_task(
            "v1.tasks.pii_tasks.run_pii_detection_task",  # full dotted path
            queue=CELERY_SPARK_QUEUE,
            args=[
                request.file_path,
                request.file_type,
                request.task_id,
                request.connection_id,
                request.account_id,
                request.service,
                request.csv_header,
                request.row_limit,
                request.col_limit,
                request.chunksize,
                request.include_address
            ]
        )
        return {
            "message": "PII scan task submitted to Celery",
            "task_id": request.task_id,
            "celery_queue": CELERY_SPARK_QUEUE,
            "celery_id": result.id
        }
    except Exception as e:
        logger.exception(f"Failed to submit task to Celery: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")