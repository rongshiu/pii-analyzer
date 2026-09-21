# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
# from pyspark.sql import SparkSession
# from fastapi.responses import JSONResponse
from typing import Dict

from utility.logger import get_logger
from v1 import api as api_v1
# from utility.spark_util import spark

logger = get_logger()

# Metadata for Swagger docs
TAGS_METADATA = [
    {
        "name": "spark-job",
        "description": "Detect PII Data",
    }
]

# CORS allowed origins (expandable in config later)
ALLOWED_ORIGINS = [
    "*"
]

# Create the FastAPI app
app = FastAPI(
    title="spark-job",
    description="An API to scan files in order to identify PII data",
    version="v1",
    openapi_tags=TAGS_METADATA,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_v1.router)

# Health check endpoint
@app.get("/health", tags=["health"])
def health() -> Dict[str, bool]:
    return {"success": True}

# Add Prometheus metrics, exclude `/metrics` itself
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app)

# Log app startup
@app.on_event("startup")
def startup_event():
    logger.info("PII Scanner Processor API has started successfully.")
    logger.info("Spark session created")

@app.on_event("shutdown")
def shutdown_event():
    # Stop SparkSession when app shuts down
    logger.info("Spark session shutdown")
    # if spark:
    #     spark.stop()