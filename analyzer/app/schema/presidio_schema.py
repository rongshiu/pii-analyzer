from pydantic import BaseModel
from typing import List

# request schema
# Base class with shared fields
class PresidioTextOnly(BaseModel):
    input_text: str

# Extends base class with extra field
class Presidio(PresidioTextOnly):
    account_id: str
    service: str
    include_address: bool = False

# response schema
class PIIDetectData(BaseModel):
    data_element: str
    start:int
    end:int
    pii_text:str
    score:float
    
class PIIDetectResponse(BaseModel):
    account_id: str
    service: str
    result: list[PIIDetectData]

# request schema
class PresidioCsv(BaseModel):
    account_id: str
    service: str
    text_list: List[PresidioTextOnly]  # Each Presidio has only input_text
    column_name: str
    chunk_index: int
    include_address: bool = False  # Moved out of text_list items

# response schema
class PIIDetectDataCsv(PIIDetectData):
    column_name: str
    chunk_index: int

class PIIDetectResponseCsv(BaseModel):
    account_id: str
    service: str
    result: list[PIIDetectDataCsv]