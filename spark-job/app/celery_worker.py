# app/celery_worker.py
import os
from celery import Celery
from utility.logger import get_logger

logger = get_logger()
# Read Redis URL from environment or fallback
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "spark_tasks",
    broker=redis_url,
    backend=redis_url,  # Optional: Store results
    include=["v1.tasks.pii_tasks", "v1.tasks.retry_completion_api"]
)

# Optional: Clean config
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # Ensures tasks are not lost on worker crash
    worker_prefetch_multiplier=1,  # Avoid task burst
)

if __name__ == "__main__":
    logger.info("Starting Celery worker...")
    logger.info(celery_app.tasks.keys())
    celery_app.start()
