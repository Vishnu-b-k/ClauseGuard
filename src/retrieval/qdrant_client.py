"""
Real Qdrant Hybrid Retrieval Client connecting to Qdrant Cloud (`cloud.qdrant.io`)
or local/in-memory vector store using FastEmbed dense embeddings.
"""

from __future__ import annotations

import logging
from typing import List
import warnings

from src.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_NAME,
    QDRANT_TIMEOUT_SEC,
)
from src.models.schemas import EvidenceSource, RetrievedEvidence, SchemaValidationError
from src.retrieval.base import RetrievalClient
from src.retrieval.qdrant_mock import _MOCK_CORPUS

# Suppress deprecation warnings from qdrant_client regarding add/query methods
warnings.filterwarnings("ignore", category=UserWarning, module="qdrant_client")


class RealQdrantRetrievalClient(RetrievalClient):
    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        timeout: float | None = None,
    ):
        warnings.filterwarnings("ignore", module="qdrant_client.*")
        warnings.filterwarnings("ignore", category=UserWarning, message=".*has been deprecated.*")
        self.url = url if url is not None else QDRANT_URL
        self.api_key = api_key if api_key is not None else QDRANT_API_KEY
        self.collection_name = collection_name if collection_name is not None else QDRANT_COLLECTION_NAME
        self.timeout = timeout if timeout is not None else QDRANT_TIMEOUT_SEC

        import qdrant_client

        if not self.url or self.url == ":memory:":
            self.client = qdrant_client.QdrantClient(":memory:")
        elif self.url.startswith("http://") or self.url.startswith("https://"):
            self.client = qdrant_client.QdrantClient(
                url=self.url,
                api_key=self.api_key if self.api_key else None,
                timeout=self.timeout,
            )
        else:
            self.client = qdrant_client.QdrantClient(path=self.url)

        self._ensure_collection_and_seed()

    def _ensure_collection_and_seed(self) -> None:
        """Ensure collection exists and seed with _MOCK_CORPUS if empty or non-existent."""
        should_seed = False
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            points_count = getattr(info, "points_count", None)
            if points_count is not None and points_count == 0:
                should_seed = True
        except Exception:
            should_seed = True

        if should_seed:
            documents = [doc["text"] for doc in _MOCK_CORPUS]
            metadata = [
                {
                    "text": doc["text"],
                    "source": doc["source"].value if hasattr(doc["source"], "value") else str(doc["source"]),
                    "metadata": doc["metadata"],
                }
                for doc in _MOCK_CORPUS
            ]
            self.client.add(
                collection_name=self.collection_name,
                documents=documents,
                metadata=metadata,
            )

    def retrieve(self, query_text: str, top_k: int = 5) -> List[RetrievedEvidence]:
        if not query_text or not query_text.strip():
            return []

        results = self.client.query(
            collection_name=self.collection_name,
            query_text=query_text,
            limit=top_k,
        )

        evidence_list: List[RetrievedEvidence] = []
        for item in results:
            payload = getattr(item, "payload", None) or getattr(item, "metadata", {})
            if not isinstance(payload, dict):
                payload = {}

            text = payload.get("text") or getattr(item, "document", "") or payload.get("document", "")
            if not text or not text.strip():
                continue

            source_raw = payload.get("source", EvidenceSource.POLICY.value)
            try:
                source = EvidenceSource(source_raw)
            except ValueError:
                source = EvidenceSource.POLICY

            meta = payload.get("metadata", {})
            if not isinstance(meta, dict):
                meta = {}

            raw_score = getattr(item, "score", 0.0)
            capped_score = round(min(max(raw_score, 0.0), 1.0), 4)

            ev = RetrievedEvidence(
                source=source,
                text=text,
                similarity_score=capped_score,
                metadata=meta,
            )
            ev.validate()
            evidence_list.append(ev)

        return evidence_list
