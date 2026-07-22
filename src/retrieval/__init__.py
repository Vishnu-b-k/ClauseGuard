"""
Retrieval module exports.
"""

from __future__ import annotations

import logging
from src.config import MOCK_MODE, QDRANT_URL
from src.retrieval.base import RetrievalClient
from src.retrieval.qdrant_mock import MockQdrantRetrievalClient
from src.retrieval.qdrant_client import RealQdrantRetrievalClient


def get_retrieval_client() -> RetrievalClient:
    """
    Factory function returning the appropriate RetrievalClient backend.
    """
    if MOCK_MODE or not QDRANT_URL:
        return MockQdrantRetrievalClient()

    try:
        return RealQdrantRetrievalClient()
    except Exception as exc:
        logging.warning(
            "Qdrant Cloud unavailable, falling back to mock: %s", exc
        )
        return MockQdrantRetrievalClient()
