CREATE TABLE pii_scanner.task_status (
    task_id TEXT,
    file_path TEXT,
    file_type TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds FLOAT,
    status TEXT,
    error_message TEXT,
    completion_api_status TEXT,
    created_at TIMESTAMP
);
CREATE INDEX idx_task_status_task_id ON pii_scanner.task_status (task_id);
