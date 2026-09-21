import os
import logging
import requests
from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log
from utility.logger import get_logger

logger = get_logger()

COMPLETION_API_ENDPOINT = f'{os.getenv("COMPLETION_API_URL")}/connector-management/internal/webhook/task'
API_KEY = os.getenv("API_KEY")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5), before_sleep=before_sleep_log(logger, logging.WARNING))
def completion_api_call(task_id):
    if not COMPLETION_API_ENDPOINT:
        logger.error("COMPLETION_API_ENDPOINT environment variable is not set")
        raise ValueError("COMPLETION_API_ENDPOINT environment variable is not set")

    url = f"{COMPLETION_API_ENDPOINT}/{task_id}/complete"

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'x-api-key': API_KEY
    }

    if BEARER_TOKEN:
        headers['Authorization'] = f"Bearer {BEARER_TOKEN}"

    logger.info(f"Calling completion API for task_id={task_id} at url={url}")
    try:
        response = requests.post(url, headers=headers, timeout=20)
        response.raise_for_status()
        logger.info(f"Successfully completed task_id={task_id} with status code {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error completing task_id={task_id}: {e}")
        raise
