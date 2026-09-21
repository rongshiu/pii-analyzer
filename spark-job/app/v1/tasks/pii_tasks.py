# app/v1/tasks/pii_tasks.py
import subprocess
import os
import time
from datetime import datetime, timedelta
from celery import shared_task
from utility.logger import get_logger
from utility.postgres_util import (
    update_completion_api_status,
    get_task_status,
    mark_task_failed,
    upsert_task_status,
    bump_exec_attempt_if_current,  # <-- NEW
)
from utility.completion_api import completion_api_call
from v1.tasks.retry_completion_api import retry_completion_api

logger = get_logger()

RETRY_DELAY_SEC     = int(os.getenv("RETRY_DELAY_SEC", "60"))        # watchdog poll cadence
MAX_RETRIES         = int(os.getenv("SUBMIT_MAX_RETRIES", "2"))      # submit attempts (timeouts / nonzero exit)
SUBMIT_TIMEOUT_SEC  = int(os.getenv("SUBMIT_TIMEOUT_SEC", "1800"))   # submit call timeout
STALE_TTL_MIN       = int(os.getenv("TASK_RUNNING_STALE_TTL_MIN", "30"))  # watchdog stale threshold
EXEC_MAX_RETRIES    = int(os.getenv("EXEC_MAX_RETRIES", "3"))        # full job reruns after driver 'failed'

# ---- finalize-once helper ---------------------------------------------------
def _finalize_once(task_id: str, final_status: str):
    """
    Fire the completion webhook exactly once per task outcome.
    completion_api_status is ONLY the notification state (not the job state):
      - pending (default)
      - in_progress
      - retry_scheduled (queued background retry)
      - success (notification sent)
      - failed (notification permanently failed)
    """
    ts = get_task_status(task_id) or {}
    cas = (ts.get("completion_api_status") or "pending").lower()

    # If we've finished or have an in-flight/scheduled notification, skip.
    if cas in ("success", "failed", "retry_scheduled", "in_progress"):
        logger.info(f"[finalize_once] task_id={task_id} completion already {cas}; skipping.")
        return

    # Mark in-progress (best-effort)
    try:
        update_completion_api_status(task_id, "in_progress")
    except Exception as e:
        logger.warning(f"[finalize_once] failed to set in_progress for {task_id}: {e}")

    # Try calling the webhook (tenacity inside completion_api_call will retry a few times)
    try:
        completion_api_call(task_id)
        try:
            update_completion_api_status(task_id, "success")
        except Exception as e:
            logger.warning(f"[finalize_once] unable to set completion_api_status=success for {task_id}: {e}")
        logger.info(f"[finalize_once] completion API OK for {task_id} (job final_status={final_status}).")
    except Exception as exc:
        logger.error(f"[finalize_once] completion_api_call failed for {task_id}: {exc}")
        # Mark retry_scheduled BEFORE enqueueing the retry to avoid races
        try:
            update_completion_api_status(task_id, "retry_scheduled")
        except Exception as e:
            logger.warning(f"[finalize_once] unable to set completion_api_status=retry_scheduled for {task_id}: {e}")
        # Schedule the delayed retry task (that task will set success/failed)
        retry_completion_api.apply_async(args=[task_id], countdown=1800)
# ----------------------------------------------------------------------------


@shared_task(bind=True, queue="spark")
def run_pii_detection_task(
    self,
    file_path,
    file_type,
    task_id,
    connection_id,
    account_id,
    service,
    csv_header,
    row_limit,
    col_limit,
    chunksize,
    include_address,
    exec_attempt=1,   # execution attempt number (1-based)
):
    """
    Submit Spark job. Retries submission issues up to MAX_RETRIES.
    Actual job-level retries (when driver writes status='failed') are handled by ensure_task_status
    by rescheduling THIS task with exec_attempt+1.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            logger.info(f"[submit_pii_job] task_id={task_id} starting (submit_attempt={attempt}, exec_attempt={exec_attempt})")

            spark_submit_cmd = [
                "spark-submit",
                "--master", os.getenv("SPARK_MASTER_URL", "local[*]"),

                # S3A / MinIO config
                "--conf", f"spark.hadoop.fs.s3a.endpoint=http://{os.environ['MINIO_ENDPOINT']}",
                "--conf", f"spark.hadoop.fs.s3a.access.key={os.environ['MINIO_ACCESS_KEY']}",
                "--conf", f"spark.hadoop.fs.s3a.secret.key={os.environ['MINIO_SECRET_KEY']}",
                "--conf", "spark.hadoop.fs.s3a.path.style.access=true",
                "--conf", "spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem",

                # Executor env
                "--conf", f"spark.executorEnv.REDIS_URL={os.environ['REDIS_URL']}",
                "--conf", f"spark.executorEnv.MINIO_ENDPOINT={os.environ['MINIO_ENDPOINT']}",
                "--conf", f"spark.executorEnv.MINIO_ACCESS_KEY={os.environ['MINIO_ACCESS_KEY']}",
                "--conf", f"spark.executorEnv.MINIO_SECRET_KEY={os.environ['MINIO_SECRET_KEY']}",
                "--conf", f"spark.executorEnv.POSTGRES_URL={os.environ['POSTGRES_URL']}",
                "--conf", f"spark.executorEnv.POSTGRES_USER={os.environ['POSTGRES_USER']}",
                "--conf", f"spark.executorEnv.POSTGRES_PASSWORD={os.environ['POSTGRES_PASSWORD']}",
                "--conf", f"spark.executorEnv.POSTGRES_DB={os.environ['POSTGRES_DB']}",
                "--conf", f"spark.executorEnv.ANALYZER_URL={os.environ['ANALYZER_URL']}",
                "--conf", f"spark.executorEnv.ANALYZER_API_KEY={os.environ['ANALYZER_API_KEY']}",
                "--conf", f"spark.executorEnv.COMPLETION_API_URL={os.environ['COMPLETION_API_URL']}",
                "--conf", f"spark.executorEnv.API_KEY={os.environ['API_KEY']}",
                "--conf", f"spark.executorEnv.BEARER_TOKEN={os.environ['BEARER_TOKEN']}",
                "--conf", "spark.executorEnv.PYTHONPATH=/app",

                # Entrypoint (driver never calls completion API)
                "v1/tasks/run_pii_entry.py",
                file_path, file_type, task_id, connection_id, account_id, service,
                str(csv_header), str(row_limit), str(col_limit), str(chunksize), str(include_address)
            ]

            subprocess.run(
                spark_submit_cmd,
                check=True,
                env={**os.environ, "PYTHONPATH": "/app"},
                timeout=SUBMIT_TIMEOUT_SEC,
            )

            logger.info(f"[submit_pii_job] task_id={task_id} submit OK (submit_attempt={attempt}, exec_attempt={exec_attempt})")

            # Start / continue watchdog loop for this exec_attempt (immediately)
            ensure_task_status.apply_async(
                kwargs=dict(
                    task_id=task_id,
                    file_path=file_path,
                    file_type=file_type,
                    connection_id=connection_id,
                    account_id=account_id,
                    service=service,
                    csv_header=csv_header,
                    row_limit=row_limit,
                    col_limit=col_limit,
                    chunksize=chunksize,
                    include_address=include_address,
                    exec_attempt=exec_attempt,    # carry attempt forward
                ),
                countdown=0
            )
            return

        except subprocess.TimeoutExpired as e:
            logger.error(f"[submit_pii_job] task_id={task_id} submit TIMED OUT (submit_attempt={attempt}, exec_attempt={exec_attempt}): {e}")
        except subprocess.CalledProcessError as e:
            logger.error(f"[submit_pii_job] task_id={task_id} submit FAILED (submit_attempt={attempt}, exec_attempt={exec_attempt}): {e}")

        if attempt >= MAX_RETRIES:
            logger.error(f"[submit_pii_job] task_id={task_id} submit retries exhausted for this exec_attempt={exec_attempt}. Marking FAILED & finalizing when retries done.")
            try:
                upsert_task_status({
                    "task_id": task_id,
                    "file_path": file_path,
                    "file_type": file_type,
                    "start_time": None,
                    "end_time": datetime.utcnow(),
                    "duration_seconds": None,
                    "status": "failed",
                    "error_message": "Submit retries exhausted",
                    "completion_api_status": "pending",
                    "account_id": account_id,
                    "service": service,
                    "exec_attempt": exec_attempt,  # stamp current exec attempt
                })
            except Exception:
                pass

            # Watchdog will see 'failed' and either resubmit or finalize
            ensure_task_status.apply_async(
                kwargs=dict(
                    task_id=task_id,
                    file_path=file_path,
                    file_type=file_type,
                    connection_id=connection_id,
                    account_id=account_id,
                    service=service,
                    csv_header=csv_header,
                    row_limit=row_limit,
                    col_limit=col_limit,
                    chunksize=chunksize,
                    include_address=include_address,
                    exec_attempt=exec_attempt,
                ),
                countdown=0
            )
            return

        time.sleep(RETRY_DELAY_SEC)
        continue


@shared_task(bind=True, queue="watchdog", max_retries=None, default_retry_delay=RETRY_DELAY_SEC, ignore_result=True)
def ensure_task_status(
    self,
    task_id,
    file_path=None,
    file_type=None,
    connection_id=None,
    account_id=None,
    service=None,
    csv_header=None,
    row_limit=None,
    col_limit=None,
    chunksize=None,
    include_address=None,
    exec_attempt=1,   # execution attempt number (1-based)
):
    """
    Watchdog:
      - If no row yet: submit once and re-check.
      - If status success: finalize-once.
      - If status failed: if exec_attempt < EXEC_MAX_RETRIES → bump in DB + resubmit; else finalize-once.
      - If running but stale > TTL: mark failed, then same retry logic.
      - Else: re-check later.
    """
    try:
        ts = get_task_status(task_id)

        if ts is None:
            logger.warning(f"[watchdog] task_id={task_id} not found. Submitting once (exec_attempt={exec_attempt}).")
            run_pii_detection_task.apply_async(kwargs=dict(
                file_path=file_path,
                file_type=file_type,
                task_id=task_id,
                connection_id=connection_id,
                account_id=account_id,
                service=service,
                csv_header=csv_header,
                row_limit=row_limit,
                col_limit=col_limit,
                chunksize=chunksize,
                include_address=include_address,
                exec_attempt=exec_attempt,
            ))
            raise self.retry(countdown=RETRY_DELAY_SEC)

        # If completion already finalized, do nothing.
        cas = (ts.get("completion_api_status") or "pending").lower()
        if cas not in ("pending", "retry_scheduled"):
            logger.info(f"[watchdog] task_id={task_id} completion already {cas}; not resubmitting.")
            return

        status = (ts.get("status") or "").lower()
        now = datetime.utcnow()
        updated_at = ts.get("updated_at")

        # Normalize attempts: trust the latest we know (DB vs kwarg)
        db_attempt = int(ts.get("exec_attempt") or 1)
        kw_attempt = int(exec_attempt or 1)
        current_attempt = max(db_attempt, kw_attempt)

        # Terminal success → finalize-once
        if status == "success":
            logger.info(f"[watchdog] task_id={task_id} success on exec_attempt={current_attempt}. Finalizing once.")
            _finalize_once(task_id, final_status="success")
            return

        # Staleness check
        is_stale = False
        if status not in ("success", "failed"):
            if updated_at and (now - updated_at) > timedelta(minutes=STALE_TTL_MIN):
                is_stale = True

        if status == "failed" or is_stale:
            reason = "stale timeout" if is_stale else "driver-reported failure"
            logger.error(f"[watchdog] task_id={task_id} {reason} at exec_attempt={current_attempt}.")

            if is_stale:
                # Record failure reason for visibility
                try:
                    mark_task_failed(task_id, f"Watchdog stale > {STALE_TTL_MIN} min")
                except Exception:
                    pass

            # Execution-level retry?
            if current_attempt >= EXEC_MAX_RETRIES:
                logger.error(f"[watchdog] task_id={task_id} execution retries exhausted (exec_attempt={current_attempt}). Finalizing as failed.")
                _finalize_once(task_id, final_status="failed")
                return

            next_attempt = current_attempt + 1
            msg = f"Retrying execution attempt {next_attempt} after {reason}"

            # Atomically bump attempt; only the winner proceeds to resubmit
            if bump_exec_attempt_if_current(task_id, current_attempt, next_attempt, msg):
                run_pii_detection_task.apply_async(kwargs=dict(
                    file_path=file_path,
                    file_type=file_type,
                    task_id=task_id,
                    connection_id=connection_id,
                    account_id=account_id,
                    service=service,
                    csv_header=csv_header,
                    row_limit=row_limit,
                    col_limit=col_limit,
                    chunksize=chunksize,
                    include_address=include_address,
                    exec_attempt=next_attempt,
                ))
            else:
                logger.info(f"[watchdog] bump skipped; another watcher already advanced task_id={task_id}.")

            # Keep polling
            raise self.retry(countdown=RETRY_DELAY_SEC)

        # Still running and not stale → recheck later
        raise self.retry(countdown=RETRY_DELAY_SEC)

    except self.MaxRetriesExceededError:
        logger.error(f"[watchdog] Max retries exceeded for task_id={task_id}.")
