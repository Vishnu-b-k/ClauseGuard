"""
Real Qdrant client implementation using qdrant-client and fastembed (FR-103).
"""

from __future__ import annotations

import os
from typing import List

from qdrant_client import QdrantClient
from src.models.schemas import EvidenceSource, RetrievedEvidence
from src.retrieval.base import RetrievalClient


class RealQdrantRetrievalClient(RetrievalClient):
    def __init__(self, collection_name: str = "legal_evidence", url: str = None):
        self.collection_name = collection_name
        self.client = QdrantClient(url=url or os.environ.get("QDRANT_URL", ":memory:"))
        self.client.set_model("BAAI/bge-small-en-v1.5") # default fastembed model

    def retrieve(self, query_text: str, top_k: int = 5) -> List[RetrievedEvidence]:
        # Perform real dense search using fastembed integration in qdrant_client
        try:
            results = self.client.query(
                collection_name=self.collection_name,
                query_text=query_text,
                limit=top_k
            )
            
            evidence_list = []
            for hit in results:
                metadata = hit.payload or {}
                source_str = metadata.get("source", "legal_clause")
                
                try:
                    source = EvidenceSource(source_str)
                except ValueError:
                    source = EvidenceSource.LEGAL_CLAUSE
                    
                evidence = RetrievedEvidence(
                    source=source,
                    text=metadata.get("text", "Unknown content"),
                    similarity_score=hit.score,
                    metadata={k: v for k, v in metadata.items() if k not in ["source", "text"]}
                )
                evidence_list.append(evidence)
                
            return evidence_list
        except Exception:
            return []
