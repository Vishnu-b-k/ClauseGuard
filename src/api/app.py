"""
FastAPI application for the Legal AI Pipeline (Slice 3).
"""

import os
import uuid
import tempfile
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.ingestion.document_parser import ingest, IngestionValidationError
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval.qdrant_mock import MockQdrantRetrievalClient
from src.api.models import PipelineResultResponse

app = FastAPI(title="Legal AI Contract Compliance API", version="1.0.0")

# Enable permissive CORS for local development.
# TODO: Add real origin allowlist before production matching the zero-trust framing.
# Also, OAuth2/JWT/TLS and rate limiting should be placed at the Enterprise API Gateway layer.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the mock dependencies once for the app lifecycle
_retrieval_client = MockQdrantRetrievalClient()
_orchestrator = LyzrWorkflowOrchestrator(retrieval_client=_retrieval_client)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/contracts/analyze", response_model=PipelineResultResponse)
def analyze_contract(file: UploadFile = File(...)):
    """
    Analyzes an uploaded contract file.
    
    TODO: Move to `async def` once real ADK/LLM calls (which are I/O-bound) are wired in.
    Currently synchronous as it runs CPU-bound mock logic.
    """
    temp_path = ""
    try:
        # Write the uploaded file to a temporary path, maintaining the extension
        suffix = os.path.splitext(file.filename)[1] if file.filename else ""
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        
        with os.fdopen(fd, "wb") as f:
            f.write(file.file.read())
            
        # Ingest the file using the existing logic (validates, scans, extracts)
        try:
            text = ingest(temp_path)
        except IngestionValidationError as e:
            # Catch known ingestion/validation errors and return 400 Bad Request
            raise HTTPException(status_code=400, detail=str(e))
        
        # Analyze using orchestrator
        contract_id = file.filename or str(uuid.uuid4())
        result = _orchestrator.run(text, contract_id=contract_id)
        
        # Return serialized dictionary; FastAPI matches this against PipelineResultResponse
        return result.to_dict()
        
    except HTTPException:
        # Re-raise known HTTP exceptions (like the 400 above)
        raise
    except Exception as e:
        # Any other unexpected exception during processing should return HTTP 500
        logging.error(f"Unexpected error analyzing contract: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        # Clean up temp file whether or not processing succeeded
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
