from pydantic import BaseModel
from typing import Optional

class SparkJob(BaseModel):
    file_path: str
    task_id: str
    connection_id: str
    file_type: str
    account_id: str
    service: str
    csv_header: Optional[bool] = True
    row_limit: Optional[int] = 1000
    col_limit: Optional[int] = 100
    chunksize: Optional[int] = 1000
    include_address: Optional[bool] = False  # Added to support address detection
