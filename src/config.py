"""
Pipeline configuration.

Values here are pulled directly from the PRD so the code and the docs
can't silently drift apart:
    CONFIDENCE_THRESHOLD -> PRD "AI Governance": "Scores < 0.8 trigger
                             mandatory human review"
    RETRIEVAL_TOP_K       -> PRD FR-103 acceptance criteria: "top-K
                             relevant clauses"
"""

import os

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

# --- Pipeline Thresholds & Rules ---
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.8"))
RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# Risk levels at or above this index (see RiskLevel.ordinal) always get a
# redline drafted, regardless of confidence.
REDLINE_TRIGGER_MIN_RISK: str = os.getenv("REDLINE_TRIGGER_MIN_RISK", "medium")

# --- Execution Mode ---
MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")

# --- Google ADK / LLM Settings ---
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-flash-latest")
LLM_TIMEOUT_SEC: float = float(os.getenv("LLM_TIMEOUT_SEC", "15.0"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

# --- Qdrant Cloud Settings ---
QDRANT_URL: str = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "legal_evidence_store")
QDRANT_TIMEOUT_SEC: float = float(os.getenv("QDRANT_TIMEOUT_SEC", "10.0"))

# --- Observability ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
