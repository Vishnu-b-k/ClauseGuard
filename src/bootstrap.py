"""Application dependency wiring.

This module is the single switch point between the local mock pipeline and
real managed services. The production branch intentionally fails closed until
the real retrieval and agent integrations are implemented.
"""

from __future__ import annotations

from src.config import AppSettings
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval.qdrant_mock import MockQdrantRetrievalClient
from src.retrieval.qdrant_real import RealQdrantRetrievalClient


def create_orchestrator(settings: AppSettings) -> LyzrWorkflowOrchestrator:
    """Create the contract-analysis workflow for the configured environment."""
    if not settings.mock_mode:
        # Use real retrieval client in production
        retrieval_client = RealQdrantRetrievalClient()
    else:
        # Use mock retrieval client in development/testing
        retrieval_client = MockQdrantRetrievalClient()

    return LyzrWorkflowOrchestrator(
        retrieval_client=retrieval_client,
        retrieval_top_k=settings.retrieval_top_k,
    )