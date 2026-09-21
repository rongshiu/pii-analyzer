# clf-api

Public entry point for the pipeline. Accepts classification jobs, dispatches them to
`spark-job`, and serves results and per-account detection specifications.

> Depends on a private internal package, so it will not build from a clean clone.
> See the [root README](../README.md).

## Build

```bash
DOCKER_BUILDKIT=1 docker build \
  --secret id=github_token,src="$GITHUB_TOKEN_FILE" \
  -t clf-api .
```

## Run

```bash
docker run --rm -it \
  -v "$PWD/app:/app" \
  -e SPARK_API_URL='http://spark-job:8080/v1/trigger-job' \
  -e POSTGRES_URL='postgresql+asyncpg://postgres:postgres@postgres:5432/postgres' \
  -p 8000:8000 \
  clf-api
```

Every endpoint requires an `X-API-KEY` header.

## Examples

Submit a CSV:

```bash
curl --location 'http://0.0.0.0:8000/v1/submit-job' \
  --header 'Content-Type: application/json' \
  --header "X-API-KEY: $API_KEY" \
  --data '{
    "file_path": "test/sample.csv",
    "task_id": "abc123",
    "connection_id": "def456",
    "file_type": "csv",
    "csv_header": false
  }'
```

Submit a PDF:

```bash
curl --location 'http://0.0.0.0:8000/v1/submit-job' \
  --header 'Content-Type: application/json' \
  --header "X-API-KEY: $API_KEY" \
  --data '{
    "file_path": "test/sample.pdf",
    "task_id": "abc123",
    "connection_id": "def456",
    "file_type": "pdf"
  }'
```

Fetch results:

```bash
curl --location 'http://0.0.0.0:8000/v1/results?task_id=abc123&limit=100&offset=0' \
  --header "X-API-KEY: $API_KEY"
```
