"""
Pipeline configuration.

Values here are pulled directly from the PRD so the code and the docs
can't silently drift apart:
    CONFIDENCE_THRESHOLD -> PRD "AI Governance": "Scores < 0.8 trigger
                             mandatory human review"
    RETRIEVAL_TOP_K       -> PRD FR-103 acceptance criteria: "top-K
                             relevant clauses"
"""

CONFIDENCE_THRESHOLD: float = 0.8
RETRIEVAL_TOP_K: int = 5

# Risk levels at or above this index (see RiskLevel.ordinal) always get a
# redline drafted, regardless of confidence.
REDLINE_TRIGGER_MIN_RISK = "medium"

MOCK_MODE: bool = True  # flips to False once real ADK/Qdrant/Lyzr creds exist
