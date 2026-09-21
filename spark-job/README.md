# spark-job

Distributed scanning tier. Pulls files from object storage, extracts text (OCR for
scanned PDFs and images), fans the content out to `analyzer` across Spark
partitions, and writes findings to Postgres.

Also hosts the Celery workers: `spark` (scan execution), `retry`
(completion-callback retries) and `watchdog` (stuck-task reaping).

> Depends on a private internal package, so it will not build from a clean clone.
> See the [root README](../README.md).

## Build

```bash
DOCKER_BUILDKIT=1 docker build \
  --secret id=github_token,src="$GITHUB_TOKEN_FILE" \
  -t spark-job .
```

## Run

```bash
docker run --rm -it \
  -v "$PWD/app:/app" \
  -p 8080:8080 \
  spark-job
```

Or directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## Workers

```bash
celery -A celery_worker.celery_app worker --loglevel=info --concurrency=2 --queues=spark
celery -A celery_worker.celery_app worker --loglevel=info --concurrency=2 --queues=retry
celery -A celery_worker.celery_app worker --loglevel=info --concurrency=10 --queues=watchdog
```
