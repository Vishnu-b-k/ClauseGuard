"""
Interface every retrieval backend must satisfy (FR-103).

The orchestrator only ever talks to this interface, never to Qdrant or
the mock directly -- that's what makes swapping in a real
qdrant-client-backed implementation a one-file change later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.models.schemas import RetrievedEvidence


class RetrievalClient(ABC):
    @abstractmethod
    def retrieve(self, query_text: str, top_k: int = 5) -> List[RetrievedEvidence]:
        """Return the top_k most relevant evidence items for query_text,
        ranked by combined dense+sparse similarity, highest first."""
        raise NotImplementedError
