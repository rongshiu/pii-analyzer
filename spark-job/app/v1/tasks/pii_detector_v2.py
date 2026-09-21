# app/v1/tasks/pii_detector_v2.py
import fitz  # PyMuPDF
import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from celery_worker import celery_app
from datetime import datetime
from math import ceil

import pandas as pd  # NEW: for Excel reading

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, lit, explode, monotonically_increasing_id, expr
from pyspark.sql.types import StringType, ArrayType, StructType, StructField, IntegerType, FloatType
from utility.minio_util import download_from_minio
from utility.postgres_util import insert_results, upsert_task_status
from utility.logger import get_logger
from utility.ocr import extract_text_from_page_with_ocr

logger = get_logger()


def analyze_text(text, include_address, account_id, service):
    try:
        payload = {
            "input_text": text,
            "include_address": include_address,
            "account_id": account_id,
            "service": service
        }
        headers = {
            "X-API-KEY": os.environ["ANALYZER_API_KEY"],
            "Content-Type": "application/json",
        }
        response = requests.post(
            f'{os.environ.get("ANALYZER_URL")}/analyzer',
            headers=headers,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success") and isinstance(data.get("results"), list):
            return data["results"]
        else:
            return [{
                "data_element": None,
                "start": None,
                "end": None,
                "pii_text": None,
                "score": None,
                "error": "Malformed success response",
            }]
    except Exception as e:
        logger.error(f"Analyzer request failed: {str(e)}")
        return [{
            "data_element": None,
            "start": None,
            "end": None,
            "pii_text": None,
            "score": None,
            "error": str(e),
        }]


def make_analyze_text_udf(include_address, account_id, service):
    def _analyze(text):
        return analyze_text(text, include_address, account_id, service)

    return udf(
        _analyze,
        ArrayType(
            StructType([
                StructField("data_element", StringType(), True),
                StructField("start", IntegerType(), True),
                StructField("end", IntegerType(), True),
                StructField("pii_text", StringType(), True),
                StructField("score", FloatType(), True),
                StructField("error", StringType(), True),
            ])
        ),
    )


def quote_col(name: str) -> str:
    return f"`{(name or '').replace('`', '``')}`"


def process_column(
    col_name,
    df,
    CHUNK_SIZE,
    file_path,
    file_type,
    task_id,
    connection_id,
    account_id,
    service,
    include_address,
    page_number=None,  # used for Excel sheet index
    sheet_name=None,   # NEW: Excel sheet name
):
    logger.info(f"--- Processing column: '{col_name}' ---")
    column_start_time = time.time()
    results = []

    col_df = df.select("row_number", expr(quote_col(col_name)).alias("text")).na.drop()
    total_rows = col_df.count()
    total_chunks = ceil(total_rows / CHUNK_SIZE) if CHUNK_SIZE > 0 else 1

    logger.info(f"Column '{col_name}' has {total_rows} rows, split into {total_chunks} chunks")

    for chunk_index in range(total_chunks):
        logger.info(f"→ Chunk {chunk_index + 1} / {total_chunks} for column '{col_name}'")

        chunk_df = (
            col_df.orderBy("row_number")
            .limit((chunk_index + 1) * CHUNK_SIZE)
            .subtract(col_df.orderBy("row_number").limit(chunk_index * CHUNK_SIZE))
        )

        text_list = [{"input_text": (row["text"] or "")} for row in chunk_df.toLocalIterator()]
        if not text_list:
            continue

        payload = {
            "account_id": account_id,
            "service": service,
            "column_name": col_name,
            "chunk_index": chunk_index,
            "text_list": text_list,
            "include_address": include_address,
        }

        try:
            headers = {
                "X-API-KEY": os.environ["ANALYZER_API_KEY"],
                "Content-Type": "application/json",
            }
            endpoint_url = f'{os.environ.get("ANALYZER_URL")}/analyzer-csv'
            response = requests.post(endpoint_url, headers=headers, json=payload, timeout=180)
            response.raise_for_status()
            result_json = response.json()

            if result_json.get("success") and isinstance(result_json.get("results"), list):
                if len(result_json["results"]) > 0:
                    logger.info(f"✅ PII detected in chunk {chunk_index + 1} of column '{col_name}'")
                    for entity in result_json["results"]:
                        entity.update({
                            "task_id": task_id,
                            "connection_id": connection_id,
                            "account_id": account_id,
                            "service": service,
                            "file_type": file_type,
                            "file_path": file_path,
                        })
                        # for Excel we carry sheet index as page_number
                        if page_number is not None:
                            entity["page_number"] = int(page_number)
                        # NEW: carry sheet_name for Excel
                        if sheet_name is not None:
                            entity["sheet_name"] = sheet_name
                        results.append(entity)
                    # stop scanning further chunks for this column once PII is found
                    break
                else:
                    logger.info(f"⛔ No PII found in chunk {chunk_index + 1} of column '{col_name}'")
        except Exception as e:
            logger.error(f"❌ Exception in chunk {chunk_index + 1} of column '{col_name}': {str(e)}")

    logger.info(f"⏱ Column '{col_name}' completed in {time.time() - column_start_time:.2f} seconds")
    return results



def run_pii_detection(
    file_path,
    file_type,
    task_id,
    connection_id,
    account_id,
    service,
    csv_header,
    row_limit,
    col_limit,
    chunksize,
    include_address,
):
    logger.info("Starting PII detection")
    start_ts = time.time()
    spark = None
    local_file = None  # used for pdf/xlsx temp file cleanup
    try:
        spark = (
            SparkSession.builder
            .appName(f"PII Scanner - {task_id}")
            .config("spark.sql.shuffle.partitions", "4")
            .getOrCreate()
        )

        hadoop_conf = spark._jsc.hadoopConfiguration()
        hadoop_conf.set("fs.s3a.endpoint", f"http://{os.environ.get('MINIO_ENDPOINT', 'minio:9000')}")
        hadoop_conf.set("fs.s3a.access.key", os.environ.get("MINIO_ACCESS_KEY", "minioadmin"))
        hadoop_conf.set("fs.s3a.secret.key", os.environ.get("MINIO_SECRET_KEY", "minioadmin"))
        hadoop_conf.set("fs.s3a.path.style.access", "true")
        hadoop_conf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")

        start_time = datetime.utcnow()
        status = "success"
        error_message = None
        results = []
        CHUNK_SIZE = max(1, int(chunksize) if chunksize else 100)

        # Write 'running' row early (for watchdog visibility)
        try:
            upsert_task_status({
                "task_id": task_id,
                "file_path": file_path,
                "file_type": file_type,
                "start_time": start_time,
                "end_time": None,
                "duration_seconds": None,
                "status": "running",
                "error_message": None,
                "completion_api_status": "pending",
                "account_id": account_id,
                "service": service,
            })
        except Exception as e:
            logger.warning(f"Unable to write initial 'running' status for {task_id}: {e}")

        # -------------------------
        # 1) CSV
        # -------------------------
        if file_type == "csv":
            logger.info("=== CSV FILE DETECTION STARTED ===")
            bucket, *key_parts = file_path.split("/", 1)
            key = key_parts[0] if key_parts else ""
            s3a_path = f"s3a://{bucket}/{key}"

            df = spark.read.option("header", csv_header).csv(s3a_path).limit(row_limit)
            if col_limit and col_limit < len(df.columns):
                df = df.select(*[expr(quote_col(c)) for c in df.columns[:col_limit]])
            df = df.withColumn("row_number", monotonically_increasing_id())

            columns = [c for c in df.columns if c != "row_number"]
            with ThreadPoolExecutor(max_workers=int(os.getenv("COLUMN_WORKERS", "2"))) as executor:
                futures = [
                    executor.submit(
                        process_column,
                        c,
                        df,
                        CHUNK_SIZE,
                        file_path,
                        file_type,
                        task_id,
                        connection_id,
                        account_id,
                        service,
                        include_address,
                        None,  # page_number not used for CSV
                        None,  # sheet_name not used for CSV
                    )
                    for c in columns
                ]
                for future in as_completed(futures):
                    results.extend(future.result())

            logger.info(f"🎯 Total detected PII entities: {len(results)}")
            logger.info("=== CSV FILE DETECTION COMPLETED ===")

        # -------------------------
        # 2) EXCEL (xlsx / xls)
        # -------------------------
        elif file_type in ("xlsx", "xls"):
            logger.info("=== EXCEL FILE DETECTION STARTED ===")
            local_file = download_from_minio(file_path)

            # Interpret csv_header similar to CSV for pandas header arg
            if isinstance(csv_header, bool):
                header = 0 if csv_header else None
            else:
                header_str = str(csv_header).lower() if csv_header is not None else "true"
                header = 0 if header_str in ("true", "1", "yes", "y") else None

            xls = pd.ExcelFile(local_file)

            for sheet_index, sheet_name in enumerate(xls.sheet_names, start=1):
                logger.info(f"--- Processing Excel sheet {sheet_index}: {sheet_name} ---")

                pandas_df = xls.parse(
                    sheet_name=sheet_name,
                    header=header,
                    nrows=row_limit or None,
                )

                if pandas_df.empty:
                    logger.info(f"Sheet {sheet_name} is empty, skipping.")
                    continue

                # Drop fully empty columns (common for "Unnamed: x" junk columns)
                pandas_df = pandas_df.dropna(axis=1, how="all")

                # Respect column limit (after dropping empty columns)
                if col_limit and col_limit < len(pandas_df.columns):
                    pandas_df = pandas_df.iloc[:, :col_limit]

                # 🔹 Standardise column names like Spark CSV:
                # - If no header (header is None): _c0, _c1, ...
                # - If header row exists: any "Unnamed: x" or blank => _c{idx}
                if header is None:
                    new_cols = [f"_c{i}" for i in range(len(pandas_df.columns))]
                else:
                    new_cols = []
                    for i, c in enumerate(pandas_df.columns):
                        col_str = str(c)
                        if (
                            not col_str.strip()
                            or col_str.lower().startswith("unnamed:")
                        ):
                            new_cols.append(f"_c{i}")
                        else:
                            new_cols.append(col_str)
                pandas_df.columns = new_cols

                # Normalize all values to string for Spark, keeping nulls as None
                def to_str_or_none(v):
                    return None if pd.isna(v) else str(v)

                for c in pandas_df.columns:
                    pandas_df[c] = pandas_df[c].map(to_str_or_none)

                # Convert to Spark DataFrame (all StringType columns)
                df_sheet = spark.createDataFrame(pandas_df)
                df_sheet = df_sheet.withColumn("row_number", monotonically_increasing_id())

                columns = [c for c in df_sheet.columns if c != "row_number"]
                with ThreadPoolExecutor(max_workers=int(os.getenv("COLUMN_WORKERS", "2"))) as executor:
                    futures = [
                        executor.submit(
                            process_column,
                            c,
                            df_sheet,
                            CHUNK_SIZE,
                            file_path,
                            file_type,
                            task_id,
                            connection_id,
                            account_id,
                            service,
                            include_address,
                            sheet_index,  # page_number = sheet index
                            sheet_name,   # NEW: sheet_name
                        )
                        for c in columns
                    ]
                    for future in as_completed(futures):
                        results.extend(future.result())

            logger.info(f"🎯 Total detected PII entities (EXCEL): {len(results)}")
            logger.info("=== EXCEL FILE DETECTION COMPLETED ===")

        # -------------------------
        # 3) PDF (row_limit used as page_limit)
        # -------------------------
        elif file_type == "pdf":
            logger.info("=== PDF FILE DETECTION STARTED ===")
            local_file = download_from_minio(file_path)
            doc = fitz.open(local_file)
            pages = []

            total_pages = doc.page_count

            # Use row_limit as page_limit; if None/invalid, scan all pages
            if row_limit is None:
                page_limit = total_pages
            else:
                try:
                    rl = int(row_limit)
                    if rl <= 0:
                        page_limit = total_pages
                    else:
                        page_limit = min(rl, total_pages)
                except Exception:
                    page_limit = total_pages

            logger.info(f"PDF has {total_pages} pages, scanning first {page_limit} pages")

            for i in range(page_limit):
                page = doc[i]
                text = page.get_text().strip()
                if not text:
                    text = extract_text_from_page_with_ocr(local_file, i + 1)
                pages.append((i + 1, text))

            if not pages:
                logger.info("No pages selected for scanning in PDF (page_limit=0)")
            else:
                pdf_df = spark.createDataFrame(pages, ["page_number", "text"])
                analyze_udf = make_analyze_text_udf(include_address, account_id, service)
                pdf_df = pdf_df.withColumn("entities", analyze_udf("text"))
                exploded = pdf_df.select("page_number", "text", explode("entities").alias("entity"))
                enriched = exploded.selectExpr(
                    f"'{task_id}' as task_id",
                    f"'{connection_id}' as connection_id",
                    f"'{file_type}' as file_type",
                    f"'{file_path}' as file_path",
                    f"'{account_id}' as account_id",
                    f"'{service}' as service",
                    "CAST(page_number AS INT) as page_number",
                    "entity.data_element",
                    "entity.start",
                    "entity.end",
                    "entity.pii_text",
                    "entity.score",
                    "entity.error",
                )

                for r in enriched.toLocalIterator():
                    results.append({
                        "task_id": task_id,
                        "connection_id": connection_id,
                        "file_type": file_type,
                        "file_path": file_path,
                        "account_id": account_id,
                        "service": service,
                        "page_number": int(r["page_number"]),
                        "sheet_name": None,  # explicit for PDFs
                        "data_element": r["data_element"],
                        "start": r["start"],
                        "end": r["end"],
                        "pii_text": r["pii_text"],
                        "score": r["score"],
                        "error": r["error"],
                    })

            logger.info(f"🎯 Total detected PII entities (PDF): {len(results)}")
            logger.info("=== PDF FILE DETECTION COMPLETED ===")

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        if results:
            insert_results(results)
        else:
            logger.info("No entities to insert into results.")

    except Exception as e:
        logger.exception(f"Error during PII detection: {str(e)}")
        status = "failed"
        error_message = str(e)[:5000]

    finally:
        end_time = datetime.utcnow()
        duration_seconds = round(time.time() - start_ts, 2)

        try:
            upsert_task_status({
                "task_id": task_id,
                "file_path": file_path,
                "file_type": file_type,
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration_seconds,
                "status": status,  # "success" or "failed"
                "error_message": error_message,
                "completion_api_status": "pending",
                "account_id": account_id,
                "service": service,
            })
        except Exception as log_error:
            logger.error(f"Failed to upsert task status: {str(log_error)}")

        try:
            # cleanup for both PDF and Excel temp files
            if file_type in ("pdf", "xlsx", "xls") and local_file and os.path.exists(local_file):
                os.remove(local_file)
        except Exception as cleanup_error:
            logger.warning(
                f"Failed to delete temp file {locals().get('local_file','<unknown>')}: {str(cleanup_error)}"
            )

        try:
            if spark:
                spark.stop()
        except Exception as spark_stop_error:
            logger.warning(f"Failed to stop Spark session: {str(spark_stop_error)}")
