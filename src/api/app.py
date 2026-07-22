"""FastAPI application for the Legal AI Pipeline."""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import PipelineResultResponse
from src.bootstrap import create_orchestrator
from src.config import AppSettings, load_settings
from src.ingestion.document_parser import (
    ALLOWED_EXTENSIONS,
    IngestionValidationError,
    ingest,
)

logger = logging.getLogger(__name__)


def _validate_upload_name(file: UploadFile) -> str:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )
    return filename


def _persist_upload(file: UploadFile, settings: AppSettings) -> str:
    """Write an upload in bounded chunks and return its temporary path."""
    filename = _validate_upload_name(file)
    suffix = Path(filename).suffix.lower()
    descriptor, temp_path = tempfile.mkstemp(suffix=suffix)
    bytes_written = 0

    try:
        with os.fdopen(descriptor, "wb") as destination:
            while chunk := file.file.read(settings.upload_chunk_size_bytes):
                bytes_written += len(chunk)
                if bytes_written > settings.max_upload_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File exceeds the maximum upload size "
                            f"of {settings.max_upload_size_bytes} bytes"
                        ),
                    )
                destination.write(chunk)
        return temp_path
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Create a configured API instance for production or test use."""
    runtime_settings = settings or load_settings()
    app = FastAPI(
        title="Legal AI Contract Compliance API",
        version="1.1.0",
        docs_url="/docs" if runtime_settings.enable_docs else None,
        redoc_url="/redoc" if runtime_settings.enable_docs else None,
        openapi_url="/openapi.json" if runtime_settings.enable_docs else None,
    )
    app.state.settings = runtime_settings
    app.state.orchestrator = create_orchestrator(runtime_settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/ready")
    def readiness() -> dict[str, str]:
        return {"status": "ready", "environment": runtime_settings.environment}

    @app.post(
        "/api/v1/contracts/analyze",
        response_model=PipelineResultResponse,
    )
    def analyze_contract(file: UploadFile = File(...)) -> dict:
        """Validate, ingest, and analyze an uploaded contract."""
        temp_path = ""
        try:
            temp_path = _persist_upload(file, runtime_settings)
            text = ingest(temp_path)
            contract_id = Path(file.filename or str(uuid.uuid4())).name
            result = app.state.orchestrator.run(text, contract_id=contract_id)
            return result.to_dict()
        except IngestionValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception:
            logger.exception("Unexpected error analyzing contract")
            raise HTTPException(
                status_code=500,
                detail="An internal server error occurred.",
            ) from None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    logger.warning("Could not remove temporary upload: %s", temp_path)

    return app


app = create_app()