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

from src.api.models import PipelineResultResponse
from src.config import LOG_LEVEL
from src.ingestion.document_parser import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    IngestionValidationError,
    ingest,
)
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval import get_retrieval_client

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


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/contracts/analyze", response_model=PipelineResultResponse)
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
        orchestrator = get_orchestrator()

        # Run CPU/network-bound orchestrator pipeline in threadpool
        result = await run_in_threadpool(orchestrator.run, text, contract_id=contract_id)

        return result.to_dict()

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
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
