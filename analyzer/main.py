import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.responses import JSONResponse
from typing import Dict
from app.utility.logger import get_logger
from app.lifecycle.lifespan import life_span
from app.v1 import api as api_v1

logger = get_logger()

# Metadata for Swagger docs
TAGS_METADATA = [
    {
        "name": "analyzer",
        "description": "Detect PII Data",
    }
]

# CORS allowed origins (expandable in config later)
ALLOWED_ORIGINS = [
    "*"
]

# Create the FastAPI app
app = FastAPI(
    title="analyzer",
    description="An API to scan text in order to identify PII data",
    version="v1",
    openapi_tags=TAGS_METADATA,
    lifespan=life_span
)
app.openapi_version = "3.0.1"

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

if __name__ == "__main__":
    # Start the server for pyinstaller
    if os.getenv("IS_LOCAL", "false").lower() != "true":
        uvicorn.run(app, host="0.0.0.0", port=3000)
