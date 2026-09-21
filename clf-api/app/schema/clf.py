from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

class ClfApi(BaseModel):
    file_path: str
    task_id: str
    connection_id: str
    account_id: str
    service: str
    file_type: str
    csv_header: Optional[bool] = True
    row_limit: Optional[int] = 1000
    col_limit: Optional[int] = 100
    chunksize: Optional[int] = 1000
    include_address: Optional[bool] = False  # Added to support address detection

class GetResult(BaseModel):
    task_id: str
    limit: int = Field(..., le=1000, description="Maximum limit is 1000")
    offset: int

class DetectionSpecificationCreate(BaseModel):
    account_id: str
    service: str
    data_elements: List[str]

class DetectionSpecificationUpdate(BaseModel):
    data_elements: List[str] = Field(default_factory=list, description="List of data elements to detect")

class DetectionSpecificationOut(BaseModel):
    account_id: str
    service: str
    data_elements: List[str]
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class SensitiveDataIdentifierResponse(BaseModel):
    status: Literal["ok"]
    supported_data_elements: List[str] = Field(default_factory=list, description="List of data elements supported")
    supported_services: List[str] = Field(default_factory=list, description="List of services supported")