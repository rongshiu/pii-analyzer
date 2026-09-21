CREATE TABLE IF NOT EXISTS pii_scanner.results (
    task_id TEXT,
    connection_id TEXT,
    file_type TEXT,
    file_path TEXT,
    chunk_index INT,
    column_name TEXT,
    page_number INT,
    data_element TEXT,
    "start" BIGINT,
    "end" BIGINT,
    pii_text TEXT,
    score FLOAT,
    error TEXT,
    created_at TIMESTAMP
);
CREATE INDEX idx_results_task_id ON pii_scanner.results (task_id);