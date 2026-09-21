# PII Analyzer & Scanner

A distributed pipeline that finds personally identifiable information in bulk document
stores. Files land in object storage, get fanned out across Spark partitions, and every
cell or page of text is checked against a detection engine tuned for **Southeast Asian
identity formats** — MyKad, Indonesian NIK, Thai national ID, Vietnamese ID — alongside
the usual credit cards, passports and IBAN/SWIFT codes.

Built as production infrastructure for a data-governance platform, handling
multi-gigabyte spreadsheets and scanned PDFs.

> [!IMPORTANT]
> **This is a code excerpt, not a runnable project.** It depends on an internal shared
> package and a private HuggingFace model that are not publicly available, so a clean
> clone will not build. It is published to show the architecture, the detection logic
> and the operational design. All credentials, internal hostnames and identifying
> references have been removed; see [Sanitisation](#sanitisation).

---

## Architecture

```
                    ┌──────────┐
   client ─────────▶│ clf-api  │  auth, job intake, results
                    └────┬─────┘
                         │ trigger
                    ┌────▼─────┐        ┌─────────┐
                    │spark-job │◀──────▶│  MinIO  │  source files
                    └────┬─────┘        └─────────┘
                         │ partitioned text
                    ┌────▼─────┐
                    │ analyzer │  Presidio + custom recognisers
                    └────┬─────┘
                         │ findings
                    ┌────▼─────┐
                    │ Postgres │  results, task_status
                    └──────────┘

   Celery queues:  spark (execution) · retry (callbacks) · watchdog (stuck tasks)
   Redis:          broker + detection-spec cache
```

### Services

| Service | Role |
|---|---|
| **`clf-api`** | Public FastAPI surface. API-key auth, job submission, paginated results, per-account detection specifications. |
| **`spark-job`** | Scanning tier. Pulls from object storage, extracts text (OCR for scanned pages), partitions across Spark, writes findings. Hosts the three Celery workers. |
| **`analyzer`** | Detection engine. [Microsoft Presidio](https://github.com/microsoft/presidio) extended with custom validators and a transformer-based address model. |
| **`alembic`** | Schema migrations for the `pii_scanner` schema. |

---

## Detection

**17 entity types**, each behind a dedicated validator rather than a bare regex:

`PERSON` · `ADDRESS` · `EMAIL_ADDRESS` · `PHONE_NUMBER` · `IP_ADDRESS` ·
`CREDIT_CARD` · `IBAN_CODE` · `SWIFT_CODE` · `PASSPORT` · `MYKAD` ·
`INDONESIAN_NIK` · `THAILAND_ID` · `VIETNAM_ID` · `VEHICLE_PLATE` ·
`CERTIFICATE_NUMBER` · `POLICY_NUMBER` · `PASSWORD`

What the validators actually do:

- **Checksum verification, not pattern matching.** Credit cards run Luhn; MyKad and NIK
  decode the embedded birth date and region code; Thai national IDs verify the mod-11
  check digit. Pattern-only matching produces far too many false positives at scale.
- **SWIFT/BIC codes** validate against a bundled library of **204 country files**, so a
  well-formed code pointing at a nonexistent bank is rejected.
- **Addresses** are detected by a fine-tuned transformer rather than rules, because
  address formats across the region resist regex entirely.
- **Detection specs are per-account.** Each tenant enables only the entity types they
  care about, cached in Redis and resolved at scan time.

---

## Engineering notes

Details that mattered in production:

- **OCR fallback.** Scanned PDFs carry no text layer, so pages that extract empty are
  re-run through Tesseract via `pdf2image`.
- **Spreadsheets scan per sheet.** `xlsx`/`xls` inputs record `sheet_name` on every
  finding, so results map back to a location a human can open.
- **Partitioned fan-out.** Text is distributed across Spark partitions and batched into
  the analyzer, keeping throughput flat as file size grows.
- **Three separate queues.** Scan execution, completion-callback retries and stuck-task
  reaping are isolated, so a downstream outage cannot stall the scanning pool.
- **Idempotent writes.** Task status upserts use `COALESCE` and an `exec_attempt`
  guard so a retried or out-of-order task never regresses recorded state.
- **Single-binary release image.** Production builds compile to a PyInstaller binary on
  `debian-slim` running as a non-root user, with the model cache baked in for offline
  inference (`TRANSFORMERS_OFFLINE=1`).

**Stack:** Python · FastAPI · Apache Spark · Celery · Redis · PostgreSQL · MinIO ·
Presidio · HuggingFace Transformers · Docker · Alembic

---

## Repository layout

```
clf-api/       job intake API, detection specs
spark-job/     scan execution, OCR, Celery workers
analyzer/      Presidio recognisers, validators, SWIFT library (204 countries)
alembic/       migrations
postgres/      schema bootstrap
```

---

## Configuration

Every secret is read from the environment. Copy [.env.example](.env.example) to `.env`
and fill it in — nothing is hardcoded.

Build-time credentials (the private package, the private model) are supplied through
**BuildKit secret mounts**, so they are never written into an image layer:

```dockerfile
RUN --mount=type=secret,id=github_token \
    pip install "git+https://$(cat /run/secrets/github_token)@github.com/ORG/..."
```

### Docker Compose

```bash
docker compose up                      # bring the stack up
docker compose up --build --no-cache   # rebuild images
docker compose down                    # stop
docker compose down -v                 # stop and clear minio_data / pg_data
```

`docker-compose-local.yml` swaps the analyzer to `Dockerfile.local`, a hot-reload image
that skips the PyInstaller step.

---

## Sanitisation

This repo was scrubbed before publication. Removed or replaced:

- All API keys, bearer tokens, GitHub PATs and HuggingFace tokens → environment variables
- Licensing credentials → environment variables (the integration structure is kept)
- Internal hostnames, private repository URLs and the private model name → placeholders
- Absolute developer paths in volume mounts → relative paths
- Company and product naming → generic equivalents

Every credential that appeared in earlier working copies has been rotated.

## Licence

Published for portfolio review. Not licensed for reuse or redistribution.
