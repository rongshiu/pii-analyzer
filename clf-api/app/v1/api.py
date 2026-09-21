import os
import json
from fastapi import APIRouter, Header, Depends, HTTPException, Request  # + Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, update, select, text
from sqlalchemy.exc import SQLAlchemyError
import sqlalchemy as sa
from datetime import datetime

from schema.clf import (
    ClfApi,
    GetResult,
    DetectionSpecificationCreate,
    DetectionSpecificationUpdate,
    DetectionSpecificationOut,
    SensitiveDataIdentifierResponse,
)
from utility.logger import get_logger
from utility.db_conn import get_db
from utility.retrieve_identifiers import get_identifiers_from_yaml
from utility.settings import SUPPORTED_DATA_ELEMENTS, SUPPORTED_SERVICES
from v1.spark_client import trigger_spark_job

from utility.redis_helper import (
    REDIS_EXPIRE_SECONDS,
    get_redis_key,
    get_or_create_redis,
    prime_allowed_elements_cache,
)

logger = get_logger()
router = APIRouter()

API_VERSION = "v1"
env = os.environ.get("HOST_ENV", "development")


@router.post(f"/{API_VERSION}/submit-job", tags=["PII Scanner"])
async def submit_job(request_data: ClfApi, x_api_key: str = Header(..., alias="X-API-KEY"),):
    t1 = datetime.utcnow()
    rst = {
        "success": True,
        "task_id": request_data.task_id,
        "submitted_at": t1.isoformat()
    }

    try:
        logger.info("Submitting job to processor...")
        response = trigger_spark_job(
            request_data.file_path,
            request_data.task_id,
            request_data.connection_id,
            request_data.account_id,
            request_data.service,
            request_data.file_type,
            request_data.csv_header,
            request_data.row_limit,
            request_data.col_limit,
            request_data.chunksize,
            request_data.include_address
        )
        rst["celery_queue"] = response.get("celery_queue")
        rst["celery_job_id"] = response.get("celery_id")
        logger.info(response)
        # rst["status"] = response.get("status") 
        logger.info(f"Successfully submitted job...")
        status_code = 202  # Accepted
    except Exception as e:
        rst["success"] = False
        rst["error"] = {"message": str(e)}
        logger.error("An error has occurred: %s", str(rst["error"]))
        status_code = 500  # Internal Server Error

    t2 = datetime.utcnow()
    logger.info("Total time: %s seconds", str((t2 - t1).total_seconds()))

    json_compatible_item_data = jsonable_encoder(rst)
    return JSONResponse(content=json_compatible_item_data, status_code=status_code)


@router.get(f"/{API_VERSION}/results", tags=["PII Scanner"])
async def get_results(params: GetResult = Depends(), db: AsyncSession = Depends(get_db), x_api_key: str = Header(..., alias="X-API-KEY"),):
    query = text("""
        select s.task_id,
            s.file_path,
            s.file_type,
            s.start_time,
            s.end_time,
            s.duration_seconds,
            s.status as task_status,
            s.error_message as task_error,
            s.created_at as task_created_at,
            r.connection_id,
            r.chunk_index,
            r.column_name,
            r.page_number,
            r.sheet_name,
            r.data_element,
            r.start,
            r.
        end,
        r.pii_text,
        r.score,
        r.error as analyzer_error,
        r.created_at as analyzer_created_at
        from pii_scanner.results r
            right join pii_scanner.task_status s on s.task_id = r.task_id
        where s.task_id = :task_id
        order by r.created_at desc,
            r.start
        limit :limit offset :offset
    """)
    result = await db.execute(
        query,
        {
            "task_id": params.task_id,
            "offset": params.offset,
            "limit": params.limit,
        }
    )
    logger.info(result)
    rows = result.mappings().all()
    return rows


@router.post(f"/{API_VERSION}/detection-specifications", tags=["PII Scanner"])
async def create_detection_spec(
    spec: DetectionSpecificationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_api_key: str = Header(..., alias="X-API-KEY"),
):
    try:
        await db.execute(
            text("""
                INSERT INTO pii_scanner.detection_specifications
                (account_id, service, data_elements)
                VALUES (:account_id, :service, :data_elements)
            """),
            {
                "account_id": spec.account_id,
                "service": spec.service,
                "data_elements": spec.data_elements,
            }
        )
        await db.commit()

        # Optional but recommended: prime Redis so analyzers see it immediately
        try:
            redis = await get_or_create_redis(request)
            await prime_allowed_elements_cache(redis, spec.account_id, spec.service, spec.data_elements)
            logger.info("Redis cache created for key=%s", get_redis_key(spec.account_id, spec.service))
        except Exception as e:
            logger.warning("Failed to prime Redis on create for %s/%s: %s", spec.account_id, spec.service, e)

        return {"success": True, "message": "Detection specification created"}
    except SQLAlchemyError as e:
        logger.error("Create error: %s", str(e))
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put(f"/{API_VERSION}/detection-specifications/{{account_id}}/{{service}}", tags=["PII Scanner"])
async def update_detection_spec(
    account_id: str,
    service: str,
    update_data: DetectionSpecificationUpdate,
    request: Request,  # <-- needed to access redis
    db: AsyncSession = Depends(get_db),
    x_api_key: str = Header(..., alias="X-API-KEY"),
):
    values = {k: v for k, v in update_data.dict().items() if v is not None}
    if not values:
        return JSONResponse(status_code=400, content={"success": False, "error": "No values to update"})

    try:
        set_clause = ", ".join([f"{key} = :{key}" for key in values.keys()])
        values["account_id"] = account_id
        values["service"] = service

        query = text(f"""
            UPDATE pii_scanner.detection_specifications
            SET {set_clause}
            WHERE account_id = :account_id AND service = :service
        """)
        result = await db.execute(query, values)
        await db.commit()

        if result.rowcount == 0:
            return JSONResponse(status_code=404, content={"success": False, "error": "Detection specification not found"})

        # Refresh Redis immediately if data_elements changed
        cache_refreshed = False
        if "data_elements" in values:
            try:
                redis = await get_or_create_redis(request)
                await prime_allowed_elements_cache(redis, account_id, service, values["data_elements"])
                logger.info("Redis cache updated for key=%s", get_redis_key(account_id, service))
                cache_refreshed = True
            except Exception as e:
                logger.warning("Failed to update Redis cache for %s/%s: %s", account_id, service, e)

        return {
            "success": True,
            "message": "Detection specification updated",
            "cache_refreshed": cache_refreshed
        }

    except SQLAlchemyError as e:
        logger.error("Update error: %s", str(e))
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get(
    f"/{API_VERSION}/detection-specifications/{{account_id}}/{{service}}",
    response_model=DetectionSpecificationOut,
    tags=["PII Scanner"]
)
async def get_detection_spec(
    account_id: str,
    service: str,
    db: AsyncSession = Depends(get_db),
    x_api_key: str = Header(..., alias="X-API-KEY"),
):
    try:
        query = text("""
            SELECT account_id, service, data_elements, created_at
            FROM pii_scanner.detection_specifications
            WHERE account_id = :account_id AND service = :service
        """)
        result = await db.execute(query, {"account_id": account_id, "service": service})
        row = result.mappings().first()

        if not row:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Detection specification not found"}
            )

        return row  # Will auto-convert to DetectionSpecificationOut

    except SQLAlchemyError as e:
        logger.error("Get error: %s", str(e))
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get(f"/{API_VERSION}/get-data-elements-and-services", description="Help to get list of data elements and services supported", tags=["PII Scanner"])
async def get_data_elements_and_svc(x_api_key : str = Header(...,alias="X-API-KEY")) -> SensitiveDataIdentifierResponse:
    
    try:
        logger.info(f"Fetching from configuration: {SUPPORTED_DATA_ELEMENTS} and {SUPPORTED_SERVICES}")
        # Fetch the sensitive data types from the configuration
        supported_data_elements = get_identifiers_from_yaml(SUPPORTED_DATA_ELEMENTS)
        supported_services = get_identifiers_from_yaml(SUPPORTED_SERVICES)
        logger.info("config retrieved...")
        return {"status":"ok",
                "supported_data_elements": supported_data_elements,
                "supported_services": supported_services
               }

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))