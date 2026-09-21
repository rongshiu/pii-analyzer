# app/v1/api.py
import os
from datetime import datetime

from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.schema.presidio_schema import Presidio, PIIDetectResponse, PIIDetectResponseCsv, PresidioCsv
from app.services.pii_detect import PIIDetectService
from app.utility.logger import get_logger
# from app.utility.get_detection_specs import get_allowed_data_elements
from app.utility.get_allowed_data_elements import get_allowed_data_elements_redis_first

from app.db.database import async_session_maker  # your session maker

logger = get_logger()
router = APIRouter()

API_VERSION = "v1"
env = os.environ.get("HOST_ENV", "development")


@router.post(f"/{API_VERSION}/analyzer", tags=["analyzer"])
async def analyzer(request_data: Presidio, request: Request, x_api_key: str = Header(..., alias="X-API-KEY")):
    rst = {"success": False, "account_id": request_data.account_id, "service": request_data.service}
    t1 = datetime.utcnow()

    try:
        logger.info("Starting PII scan...")
        redis = request.app.state.redis
        async with async_session_maker() as session:
            allowed_data_elements = await get_allowed_data_elements_redis_first(
                db=session,
                redis=redis,
                account_id=request_data.account_id,
                service=request_data.service
            )

        pii_detect_service: PIIDetectService = request.app.state.pii_detect_service
        results = pii_detect_service.analyse_text(
            text=request_data.input_text,
            allowed_data_elements=allowed_data_elements,
            include_address=request_data.include_address
        )

        response_model = PIIDetectResponse(
            account_id=request_data.account_id,
            service=request_data.service,
            result=results
        )
        rst["results"] = response_model.result
        rst["success"] = True
        status_code = 200

    except HTTPException as e:
        # Re-raise to preserve intended status code (e.g., 404)
        logger.warning(f"HTTPException during analyzer: {e.detail} (status={e.status_code})")
        raise e

    except Exception as e:
        rst["error"] = {"message": str(e)}
        logger.error("An error has occurred: %s", str(e))
        status_code = 500

    t2 = datetime.utcnow()
    logger.info("Total time: %s seconds", str((t2 - t1).total_seconds()))
    return JSONResponse(content=jsonable_encoder(rst), status_code=status_code)


@router.post(f"/{API_VERSION}/analyzer-csv", tags=["analyzer"])
async def analyzer_csv(request_data: PresidioCsv, request: Request, x_api_key: str = Header(..., alias="X-API-KEY")):
    rst = {"success": False, "account_id": request_data.account_id, "service": request_data.service}
    t1 = datetime.utcnow()

    try:
        logger.info("Starting PII CSV scan...")
        redis = request.app.state.redis
        async with async_session_maker() as session:
            allowed_data_elements = await get_allowed_data_elements_redis_first(
                db=session,
                redis=redis,
                account_id=request_data.account_id,
                service=request_data.service
            )

        pii_detect_service: PIIDetectService = request.app.state.pii_detect_service
        results = pii_detect_service.analyse_text_csv(
            text_list=request_data.text_list,
            column_name=request_data.column_name,
            chunk_index=request_data.chunk_index,
            allowed_data_elements=allowed_data_elements,
            include_address=request_data.include_address
        )

        response_model = PIIDetectResponseCsv(
            account_id=request_data.account_id,
            service=request_data.service,
            result=results
        )
        rst["results"] = response_model.result
        rst["success"] = True
        status_code = 200

    except HTTPException as e:
        # Re-raise to preserve intended status code (e.g., 404)
        logger.warning(f"HTTPException during analyzer: {e.detail} (status={e.status_code})")
        raise e

    except Exception as e:
        rst["error"] = {"message": str(e)}
        logger.error("An error has occurred: %s", str(e))
        status_code = 500

    t2 = datetime.utcnow()
    logger.info("Total time: %s seconds", str((t2 - t1).total_seconds()))
    return JSONResponse(content=jsonable_encoder(rst), status_code=status_code)
