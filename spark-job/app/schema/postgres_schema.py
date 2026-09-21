from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base

# Define the SQLAlchemy base and model
Base = declarative_base()

class PiiScanResult(Base):
    __tablename__ = "pii_scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255))
    connection_id = Column(String(255))
    file_type = Column(String(100))
    location_number = Column(Integer)
    data_element = Column(String(255))
    start_pos = Column(Integer)
    end_pos = Column(Integer)
    text = Column(Text)
    score = Column(Float)
    error = Column(Text)