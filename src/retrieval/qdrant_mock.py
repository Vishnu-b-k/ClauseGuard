"""
MOCK Qdrant Hybrid Retrieval Engine (FR-103).

TODO: replace this whole class with a real implementation backed by
`qdrant_client.QdrantClient`, querying the actual "Qdrant Legal Evidence
Store" (QDB) collection with dense embeddings (e.g. via FastEmbed, matching
the architecture) + sparse vectors, per the PRD's Qdrant Hybrid Retrieval
Engine component. Keep the class name, constructor signature, and
`retrieve()` contract identical so the orchestrator needs zero changes.

The scoring below is a genuine (if simplified) hybrid: a sparse-style
keyword-overlap score plus a dense-style bigram-similarity score,
weighted 50/50 -- not literally the Qdrant algorithm, but structurally
the same "two signals combined" pattern, so the mock's ranking behavior
is a reasonable stand-in during development.
"""

from __future__ import annotations

import re
from typing import List

from src.models.schemas import EvidenceSource, RetrievedEvidence
from src.retrieval.base import RetrievalClient

# Stand-in for the Qdrant Legal Evidence Store (QDB) + Legal Knowledge &
# Policy DB (PDB) contents. In production these come from the real
# collections; here they're seed data so retrieve() has something to rank.
_MOCK_CORPUS: list[dict] = [
    {
        "text": "Standard clause: Each party's aggregate liability under this "
        "Agreement shall not exceed the total fees paid in the twelve (12) "
        "months preceding the claim.",
        "source": EvidenceSource.STANDARD_CLAUSE,
        "metadata": {"category": "liability", "risk_baseline": "low"},
    },
    {
        "text": "Policy: Liability clauses without a cap, or with unlimited or "
        "uncapped liability language, require Legal and Risk sign-off before "
        "execution.",
        "source": EvidenceSource.POLICY,
        "metadata": {"category": "liability", "policy_id": "POL-LIAB-01"},
    },
    {
        "text": "Standard clause: This Agreement shall automatically renew for "
        "successive one (1) year terms unless either party provides written "
        "notice of non-renewal at least thirty (30) days prior to the end of "
        "the then-current term.",
        "source": EvidenceSource.STANDARD_CLAUSE,
        "metadata": {"category": "renewal", "risk_baseline": "low"},
    },
    {
        "text": "Policy: Auto-renewal clauses must include an opt-in or advance "
        "notice mechanism of at least 30 days; perpetual or evergreen renewal "
        "without a notice window is prohibited.",
        "source": EvidenceSource.POLICY,
        "metadata": {"category": "renewal", "policy_id": "POL-RENEW-02"},
    },
    {
        "text": "Standard clause: Either party may terminate this Agreement for "
        "convenience upon sixty (60) days' written notice to the other party.",
        "source": EvidenceSource.STANDARD_CLAUSE,
        "metadata": {"category": "termination", "risk_baseline": "low"},
    },
    {
        "text": "Policy: Unilateral termination rights (termination 'at sole "
        "discretion' or 'for any reason' with no notice period) require "
        "Compliance Officer approval.",
        "source": EvidenceSource.POLICY,
        "metadata": {"category": "termination", "policy_id": "POL-TERM-03"},
    },
    {
        "text": "Standard clause: Each party shall indemnify the other only for "
        "direct damages arising from its own gross negligence or willful "
        "misconduct, excluding indirect or consequential damages.",
        "source": EvidenceSource.STANDARD_CLAUSE,
        "metadata": {"category": "indemnification", "risk_baseline": "low"},
    },
    {
        "text": "Policy: Broad or one-sided indemnification obligations (e.g. "
        "'indemnify for any and all claims regardless of cause') exceed "
        "enterprise risk tolerance and must be redlined.",
        "source": EvidenceSource.POLICY,
        "metadata": {"category": "indemnification", "policy_id": "POL-INDEM-04"},
    },
    {
        "text": "Standard clause: Confidential Information shall be protected "
        "for a period of five (5) years following disclosure, with standard "
        "carve-outs for information that is public, independently developed, "
        "or required to be disclosed by law.",
        "source": EvidenceSource.STANDARD_CLAUSE,
        "metadata": {"category": "confidentiality", "risk_baseline": "low"},
    },
    {
        "text": "Policy: Confidentiality terms exceeding ten (10) years, or "
        "omitting standard carve-outs, require Legal review.",
        "source": EvidenceSource.POLICY,
        "metadata": {"category": "confidentiality", "policy_id": "POL-CONF-05"},
    },
]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _bigrams(text: str) -> set[str]:
    tokens = re.findall(r"[a-z]{2,}", text.lower())
    return {f"{a}_{b}" for a, b in zip(tokens, tokens[1:])}


def _sparse_score(query: str, doc: str) -> float:
    """Keyword-overlap score, stands in for Qdrant's sparse vector search."""
    q_tokens, d_tokens = _tokenize(query), _tokenize(doc)
    if not q_tokens or not d_tokens:
        return 0.0
    overlap = q_tokens & d_tokens
    return len(overlap) / len(q_tokens)


def _dense_score(query: str, doc: str) -> float:
    """Bigram-Jaccard score, stands in for Qdrant's dense embedding search."""
    q_bigrams, d_bigrams = _bigrams(query), _bigrams(doc)
    if not q_bigrams or not d_bigrams:
        return 0.0
    union = q_bigrams | d_bigrams
    if not union:
        return 0.0
    return len(q_bigrams & d_bigrams) / len(union)


class MockQdrantRetrievalClient(RetrievalClient):
    def __init__(self, corpus: list[dict] | None = None):
        self._corpus = corpus if corpus is not None else _MOCK_CORPUS

    def retrieve(self, query_text: str, top_k: int = 5) -> List[RetrievedEvidence]:
        scored: list[tuple[float, dict]] = []
        for doc in self._corpus:
            sparse = _sparse_score(query_text, doc["text"])
            dense = _dense_score(query_text, doc["text"])
            combined = 0.5 * sparse + 0.5 * dense
            if combined > 0:
                scored.append((combined, doc))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        results: List[RetrievedEvidence] = []
        for score, doc in scored[:top_k]:
            evidence = RetrievedEvidence(
                source=doc["source"],
                text=doc["text"],
                similarity_score=round(min(score, 1.0), 4),
                metadata=doc["metadata"],
            )
            evidence.validate()
            results.append(evidence)
        return results
