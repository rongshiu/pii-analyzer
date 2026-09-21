import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.services.pii_detect import PIIDetectService
from app.models.address_recognizer import HuggingFaceAddressRecognizer
from license_sdk import LicenseImpl
from app.utility.logger import get_logger
from app.utility.get_cache_dir import resolve_cache_dir
from app.utility.licensing import error_handling, get_fingerprint
from app.utility.version import (
    __keygen_token__, __version__,
    __keygen_product__, __keygen_account__,
    __keygen_public_key__
)
from app.utility.redis_connection import init_redis, close_redis

logger = get_logger()

@asynccontextmanager
async def life_span(app: FastAPI):
    logger.info("Application startup: entering lifespan.")

    # === License validation ===
    if __version__ != "dev":
        logger.debug("Running license validation")
        manager = LicenseImpl(
            logger,
            "analyzer-api",
            __keygen_token__,
            __keygen_product__,
            __version__,
            get_fingerprint(__keygen_product__),
        )

        err = manager.license_check()
        error_handling(err)

        # Background license monitor every 5 minutes
        manager.start_license_monitor(5 * 60, error_handling)
    else:
        logger.debug(f"No license validation required for version: {__version__}")

    # === Model loading ===
    model_cache_dir = resolve_cache_dir()
    logger.info(f"Resolving model cache dir: {model_cache_dir}")

    logger.info("Initializing HuggingFaceAddressRecognizer model...")
    address_model = HuggingFaceAddressRecognizer(
        cache_dir=model_cache_dir,
        model_name_or_path=os.getenv("HF_ADDRESS_DETECTOR_MODEL", "org/address-detector")  # private model; set via env
    )
    logger.info("Model loaded successfully.")

    logger.info("Initializing PIIDetectService with address recognizer...")
    app.state.pii_detect_service = PIIDetectService(address_model)
    logger.info("PIIDetectService initialized and ready.")

    logger.info("Initializing Redis connection...")
    redis_instance = await init_redis()
    app.state.redis = redis_instance
    logger.info("Redis connection initialized.")

    yield

    await close_redis(app.state.redis)
    logger.info("Application shutdown: exiting lifespan.")
