# app/utility/postgres_util.py
import psycopg2
import os
import math

def get_postgres_connection():
    return psycopg2.connect(
        dbname=os.environ.get("POSTGRES_DB", "postgres"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=5432
    )

def safe_int(value):
    try:
        return int(value) if value is not None and not (isinstance(value, float) and math.isnan(value)) else None
    except Exception:
        return None

# ------------------ RESULTS: unchanged ------------------
def insert_results(rows):
    conn = get_postgres_connection()
    cur = conn.cursor()

    for row in rows:
        cur.execute("""
            INSERT INTO pii_scanner.results (
                task_id, connection_id, file_type, file_path,
                chunk_index, column_name, page_number, sheet_name,
                data_element, "start", "end", pii_text, score, error,
                account_id, service, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            row.get("task_id"),
            row.get("connection_id"),
            row.get("file_type"),
            row.get("file_path"),
            row.get("chunk_index"),
            row.get("column_name"),
            row.get("page_number"),
            row.get("sheet_name"),
            row.get("data_element"),
            safe_int(row.get("start")),
            safe_int(row.get("end")),
            row.get("pii_text"),
            row.get("score"),
            row.get("error"),
            row.get("account_id"),
            row.get("service"),
        ))

    conn.commit()
    cur.close()
    conn.close()


# ------------------ TASK STATUS: upsert with UNIQUE(task_id) ------------------
def upsert_task_status(task_status: dict):
    """
    Upsert keyed by UNIQUE(task_id).
    - On INSERT: sets created_at = NOW(), updated_at = NOW()
    - On UPDATE: preserves created_at, sets updated_at = NOW()
    - completion_api_status is preserved unless a non-NULL is provided.
    - exec_attempt increases monotonically (never decreases).
    """
    payload = dict(task_status)
        # --- HARDEN exec_attempt: treat missing/None/invalid/<=0 as 1
    try:
        ea = payload.get("exec_attempt")
        payload["exec_attempt"] = 1 if ea is None else max(1, int(ea))
    except Exception:
        payload["exec_attempt"] = 1

    conn = get_postgres_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pii_scanner.task_status (
                    task_id, file_path, file_type, start_time, end_time,
                    duration_seconds, status, error_message, completion_api_status,
                    account_id, service, exec_attempt, created_at, updated_at
                )
                VALUES (
                    %(task_id)s, %(file_path)s, %(file_type)s, %(start_time)s, %(end_time)s,
                    %(duration_seconds)s, %(status)s, %(error_message)s, %(completion_api_status)s,
                    %(account_id)s, %(service)s, %(exec_attempt)s, NOW(), NOW()
                )
                ON CONFLICT (task_id) DO UPDATE SET
                    file_path             = EXCLUDED.file_path,
                    file_type             = EXCLUDED.file_type,
                    start_time            = COALESCE(EXCLUDED.start_time, pii_scanner.task_status.start_time),
                    end_time              = COALESCE(EXCLUDED.end_time,   pii_scanner.task_status.end_time),
                    duration_seconds      = COALESCE(EXCLUDED.duration_seconds, pii_scanner.task_status.duration_seconds),
                    status                = EXCLUDED.status,
                    error_message         = EXCLUDED.error_message,
                    completion_api_status = COALESCE(EXCLUDED.completion_api_status, pii_scanner.task_status.completion_api_status),
                    -- only increase exec_attempt; ignore NULLs and smaller numbers
                    exec_attempt          = CASE
                                               WHEN EXCLUDED.exec_attempt IS NULL THEN pii_scanner.task_status.exec_attempt
                                               WHEN EXCLUDED.exec_attempt >  pii_scanner.task_status.exec_attempt
                                                 THEN EXCLUDED.exec_attempt
                                               ELSE pii_scanner.task_status.exec_attempt
                                            END,
                    account_id            = EXCLUDED.account_id,
                    service               = EXCLUDED.service,
                    updated_at            = NOW()
            """, payload)
    finally:
        conn.close()

def update_completion_api_status(task_id: str, completion_api_status: str):
    conn = get_postgres_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                UPDATE pii_scanner.task_status
                   SET completion_api_status = %s,
                       updated_at = NOW()
                 WHERE task_id = %s
            """, (completion_api_status, task_id))
    finally:
        conn.close()

def get_task_status(task_id: str):
    """
    Return a dict of the task_status row (selected columns) or None if missing.
    Keys: task_id, status, start_time, end_time, updated_at, error_message,
          completion_api_status, exec_attempt
    """
    sql = """
      SELECT task_id, status, start_time, end_time, updated_at,
             error_message, completion_api_status, exec_attempt
        FROM pii_scanner.task_status
       WHERE task_id = %s
       LIMIT 1
    """
    conn = get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (task_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()

def mark_task_failed(task_id: str, message: str):
    """
    Mark a task as failed, set end_time=NOW(), update error_message, bump updated_at.
    """
    sql = """
      UPDATE pii_scanner.task_status
         SET status = 'failed',
             error_message = %s,
             end_time = NOW(),
             updated_at = NOW()
       WHERE task_id = %s
    """
    conn = get_postgres_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, (message, task_id))
    finally:
        conn.close()

# --------- Atomic bump for exec_attempt (CAS) ----------
def bump_exec_attempt_if_current(task_id: str, from_attempt: int, to_attempt: int, message: str) -> bool:
    """
    Atomically bump exec_attempt from 'from_attempt' to 'to_attempt' and mark as queued.
    Returns True if the bump happened (we were the winner), False otherwise.
    """
    sql = """
      UPDATE pii_scanner.task_status
         SET exec_attempt = %s,
             status = 'queued',
             error_message = %s,
             updated_at = NOW()
       WHERE task_id = %s
         AND exec_attempt = %s
      RETURNING 1
    """
    conn = get_postgres_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, (to_attempt, message, task_id, from_attempt))
            return cur.fetchone() is not None
    finally:
        conn.close()
