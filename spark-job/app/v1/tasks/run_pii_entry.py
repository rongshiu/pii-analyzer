# app/v1/tasks/run_pii_entry.py
import sys
from v1.tasks.pii_detector_v2 import run_pii_detection

if __name__ == "__main__":
    file_path = sys.argv[1]
    file_type = sys.argv[2]
    task_id = sys.argv[3]
    connection_id = sys.argv[4]
    account_id = sys.argv[5]  # Added for account_id
    service = sys.argv[6]  # Added for service
    csv_header = sys.argv[7].lower() == "true"
    row_limit = int(sys.argv[8])
    col_limit = int(sys.argv[9])
    chunksize = int(sys.argv[10])
    include_address = sys.argv[11].lower() == "true"

    run_pii_detection(file_path, file_type, task_id, connection_id, account_id, service, csv_header, row_limit, col_limit, chunksize, include_address)
