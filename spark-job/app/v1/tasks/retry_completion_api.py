# app/v1/tasks/retry_completion_api.py
from celery import shared_task
from utility.logger import get_logger
from utility.postgres_util import update_completion_api_status
from utility.completion_api import completion_api_call

logger = get_logger()

@shared_task(bind=True, queue="retry", autoretry_for=(), max_retries=1, default_retry_delay=3600)
def retry_completion_api(self, task_id):
    try:
        completion_api_call(task_id)
        logger.info(f"[RETRY] completion_api_call for task_id={task_id} succeeded.")
        update_completion_api_status(task_id=task_id, completion_api_status="success")
    except Exception as exc:
        logger.error(f"[RETRY] completion_api_call for task_id={task_id} failed again: {exc}")
        try:
            self.retry(exc=exc, countdown=3600)  # retry once after 60 minutes
        except self.MaxRetriesExceededError:
            update_completion_api_status(task_id=task_id, completion_api_status="failed")
            logger.error(f"[RETRY] task_id={task_id} reached max retries.")