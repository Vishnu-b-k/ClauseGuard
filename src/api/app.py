"""
FastAPI application for the Legal AI Pipeline (Slice 3 & Phase 4).
Upgraded to async execution (`async def`) with correlation IDs, structured logging, and threadpool delegation.
"""

import contextvars
import logging
import os
import tempfile
import uuid
from typing import Callable

import tenacity
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from src.models.schemas import PipelineResult as PipelineResultResponse
from src.config import LOG_LEVEL
from src.ingestion.document_parser import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    IngestionValidationError,
    ingest,
)
from src.worker.celery_app import process_contract_task, celery_app
from celery.result import AsyncResult
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval import get_retrieval_client
from src.storage.s3_client import S3StorageClient

# --- Context and Logging Setup ---
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


# Configure structured logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(correlation_id)s] %(message)s",
    force=True,
)
logger = logging.getLogger()
logger.addFilter(CorrelationIdFilter())
for handler in logger.handlers:
    handler.addFilter(CorrelationIdFilter())

app = FastAPI(title="Legal AI Contract Compliance API", version="1.0.0")

# Enable permissive CORS for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Callable):
    corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")
    if not corr_id:
        corr_id = str(uuid.uuid4())
    token = correlation_id_var.set(corr_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response
    finally:
        correlation_id_var.reset(token)


def get_orchestrator() -> LyzrWorkflowOrchestrator:
    """Dynamically initializes orchestrator with get_retrieval_client so MOCK_MODE changes take effect."""
    retrieval_client = get_retrieval_client()
    return LyzrWorkflowOrchestrator(retrieval_client=retrieval_client)


# Initialize default module-level dependencies for compatibility with existing references
_retrieval_client = get_retrieval_client()
_orchestrator = LyzrWorkflowOrchestrator(retrieval_client=_retrieval_client)
_s3_client = S3StorageClient()


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/contracts/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    """
    Analyzes an uploaded contract file asynchronously without blocking the event loop.
    Delegates CPU/network-bound agent and retrieval logic to a threadpool.
    """
    temp_path = ""
    try:
        suffix = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{suffix}'. Unsupported file format. Must be .pdf, .docx, or .txt.",
            )

        if getattr(file, "size", None) is not None and file.size > MAX_FILE_SIZE_BYTES:  # type: ignore[operator]
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 25MB.")

        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 25MB.")

        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(content)

        try:
            text = ingest(temp_path)
        except IngestionValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        contract_id = file.filename or str(uuid.uuid4())
        s3_key = f"contracts/{contract_id}-{uuid.uuid4()}{suffix}"

        # Upload original document to Contract Object Storage
        try:
            _s3_client.upload_file(content, s3_key)
            logger.info(f"Uploaded contract to S3 with key: {s3_key}")
        except Exception as e:
            logger.warning(f"Failed to upload to S3 (continuing analysis): {e}")

        # Dispatch async task to RabbitMQ / Celery
        task = process_contract_task.delay(contract_id, text)

        return {"status": "processing", "contract_id": contract_id, "task_id": task.id}

    except HTTPException:
        raise
    except (TimeoutError, tenacity.RetryError) as e:
        logger.error(f"Timeout during contract analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="AI reasoning or vector store timed out. Please try again.",
        )
    except Exception as e:
        corr_id = correlation_id_var.get()
        logger.error(
            f"Unexpected error analyzing contract [correlation_id={corr_id}]: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

@app.get("/api/v1/contracts/{task_id}/status")
async def get_contract_status(task_id: str):
    """
    Checks the status of a background contract analysis task.
    """
    res = AsyncResult(task_id, app=celery_app)
    
    if res.state == 'PENDING':
        return {"status": "processing", "state": res.state}
    elif res.state != 'FAILURE':
        if res.ready():
            return {"status": "completed", "state": res.state, "result": res.get()}
        else:
            return {"status": "processing", "state": res.state}
    else:
        # Task failed
        raise HTTPException(status_code=500, detail=str(res.info))

