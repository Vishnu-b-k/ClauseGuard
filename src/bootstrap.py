"""Application dependency wiring.

This module is the single switch point between the local mock pipeline and
real managed services. The production branch intentionally fails closed until
the real retrieval and agent integrations are implemented.
"""

from __future__ import annotations

from src.config import AppSettings
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval.qdrant_mock import MockQdrantRetrievalClient


def create_orchestrator(settings: AppSettings) -> LyzrWorkflowOrchestrator:
    """Create the contract-analysis workflow for the configured environment."""
    if not settings.mock_mode:
        raise RuntimeError(
            "Real service integrations are not configured yet. "
            "Set MOCK_MODE=true only for local development, or complete the "
            "Qdrant and ADK integration before deploying this environment."
        )

    return LyzrWorkflowOrchestrator(
        retrieval_client=MockQdrantRetrievalClient(),
        retrieval_top_k=settings.retrieval_top_k,
    )