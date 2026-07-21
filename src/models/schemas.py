"""
Core data contracts for the Legal AI Contract Compliance pipeline.

PRD traceability:
    FR-102  Clause Segmentation        -> Clause
    FR-103  Hybrid Retrieval (RAG)     -> RetrievedEvidence
    FR-104  Multi-Agent Reasoning      -> AgentFinding
    FR-105  Structured Output Validation -> validate() on every model below
    FR-107  Human-in-the-Loop Feedback -> PipelineResult.flagged_for_review

Production note (FR-105 says "Validate all LLM outputs against Pydantic
schemas"): these are plain dataclasses, not pydantic.BaseModel, because this
sandbox has no network access to `pip install pydantic`. They mirror the
field names/types pydantic models would use and each carries its own
validate() method, so migrating is mechanical:

    @dataclass                      class Clause(BaseModel):
    class Clause:               ->      clause_id: str
        clause_id: str                  ...
        ...                          (drop validate(), add pydantic validators)

requirements.txt lists pydantic under the "next step" section for exactly
this swap once the environment has package access.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class SchemaValidationError(ValueError):
    """Raised when a model fails validate(). Stands in for pydantic's
    ValidationError so FR-105's "malformed output triggers repair or
    escalation" behavior can be implemented against either."""


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def ordinal(cls, level: "RiskLevel") -> int:
        return [cls.LOW, cls.MEDIUM, cls.HIGH, cls.CRITICAL].index(level)


class EvidenceSource(str, Enum):
    LEGAL_CLAUSE = "legal_clause"
    STANDARD_CLAUSE = "standard_clause"
    POLICY = "policy"
    HUMAN_VERIFIED = "human_verified_evidence"  # FR-107


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Clause:
    """One segmented clause from a contract. Produced by
    src/ingestion/clause_segmenter.py (FR-102)."""

    contract_id: str
    text: str
    clause_id: str = field(default_factory=lambda: _new_id("C"))
    clause_type_guess: Optional[str] = None  # e.g. "liability", "termination"
    start_offset: int = 0
    end_offset: int = 0

    def validate(self) -> None:
        if not self.text or not self.text.strip():
            raise SchemaValidationError(f"{self.clause_id}: clause text is empty")
        if self.end_offset < self.start_offset:
            raise SchemaValidationError(f"{self.clause_id}: invalid offsets")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RetrievedEvidence:
    """One hit from the Qdrant Hybrid Retrieval Engine (FR-103)."""

    source: EvidenceSource
    text: str
    similarity_score: float  # combined dense+sparse score, 0..1
    evidence_id: str = field(default_factory=lambda: _new_id("EV"))
    metadata: dict = field(default_factory=dict)

    def validate(self) -> None:
        if not 0.0 <= self.similarity_score <= 1.0:
            raise SchemaValidationError(
                f"{self.evidence_id}: similarity_score {self.similarity_score} out of range"
            )
        if not self.text.strip():
            raise SchemaValidationError(f"{self.evidence_id}: evidence text is empty")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        return d


@dataclass
class AgentFinding:
    """Structured output of the Legal Intelligence Agent (FR-104).
    This is the object the Deterministic Policy Validator would consume
    in the next sprint slice -- kept here so that hookup is a no-op."""

    clause_id: str
    risk_level: RiskLevel
    confidence: float  # 0..1 -- PRD AI Governance: <0.8 forces human review
    rationale: str
    cited_evidence_ids: list[str] = field(default_factory=list)
    policy_refs: list[str] = field(default_factory=list)
    finding_id: str = field(default_factory=lambda: _new_id("F"))
    generated_at: str = field(default_factory=_utcnow)

    def validate(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise SchemaValidationError(
                f"{self.finding_id}: confidence {self.confidence} out of range"
            )
        if not self.cited_evidence_ids:
            # PRD AI Governance: "agents must cite Qdrant evidence IDs"
            raise SchemaValidationError(
                f"{self.finding_id}: no evidence cited -- ungrounded finding"
            )
        if not self.rationale.strip():
            raise SchemaValidationError(f"{self.finding_id}: missing rationale")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        return d


@dataclass
class RedlineSuggestion:
    """Structured output of the Redline & Summary Agent (FR-104)."""

    clause_id: str
    original_text: str
    suggested_text: str
    rationale: str
    executive_summary: str
    redline_id: str = field(default_factory=lambda: _new_id("R"))

    def validate(self) -> None:
        if self.suggested_text.strip() == self.original_text.strip():
            raise SchemaValidationError(
                f"{self.redline_id}: suggested_text is identical to original"
            )
        if not self.rationale.strip():
            raise SchemaValidationError(f"{self.redline_id}: missing rationale")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PolicyRuleResult:
    """One policy rule that fired during deterministic validation (FR-106).
    Part of the AI Governance explainability requirement: every decision
    carries a reasoning trail of which specific rules fired and why."""

    rule_id: str
    description: str
    action: str  # human-readable summary of what the rule did

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PolicyDecision:
    """Aggregate output of the Deterministic Policy Validator (FR-106).
    Wraps an AgentFinding with the validator's final, auditable determination.

    PRD traceability:
        FR-106  Deterministic Policy Validation -> this class
        AI Governance / Explainability         -> rules_fired list
        AI Governance / Confidence Thresholds  -> requires_human_review
    """

    finding_id: str
    clause_id: str
    original_risk_level: RiskLevel
    original_confidence: float
    final_risk_level: RiskLevel
    requires_human_review: bool
    rules_fired: list[PolicyRuleResult] = field(default_factory=list)
    decision_id: str = field(default_factory=lambda: _new_id("PD"))

    def validate(self) -> None:
        if RiskLevel.ordinal(self.final_risk_level) < RiskLevel.ordinal(self.original_risk_level):
            raise SchemaValidationError(
                f"{self.decision_id}: final risk level ({self.final_risk_level.value}) "
                f"cannot be lower than original ({self.original_risk_level.value})"
            )

    def to_dict(self) -> dict:
        return {
            "finding_id": self.finding_id,
            "clause_id": self.clause_id,
            "original_risk_level": self.original_risk_level.value,
            "original_confidence": self.original_confidence,
            "final_risk_level": self.final_risk_level.value,
            "requires_human_review": self.requires_human_review,
            "rules_fired": [r.to_dict() for r in self.rules_fired],
            "decision_id": self.decision_id,
        }


@dataclass
class PipelineResult:
    """Top-level aggregate returned by the Lyzr Orchestrator for one contract."""

    contract_id: str
    clauses_processed: int
    findings: list[AgentFinding] = field(default_factory=list)
    redlines: list[RedlineSuggestion] = field(default_factory=list)
    flagged_for_review: list[str] = field(default_factory=list)  # clause_ids, FR-106/FR-107
    policy_decisions: list[PolicyDecision] = field(default_factory=list)  # FR-106
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0

    def validate(self) -> None:
        if self.clauses_processed < 0:
            raise SchemaValidationError("clauses_processed cannot be negative")
        if len(self.findings) > self.clauses_processed:
            raise SchemaValidationError("more findings than clauses processed")

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "clauses_processed": self.clauses_processed,
            "findings": [f.to_dict() for f in self.findings],
            "redlines": [r.to_dict() for r in self.redlines],
            "flagged_for_review": self.flagged_for_review,
            "policy_decisions": [d.to_dict() for d in self.policy_decisions],
            "warnings": self.warnings,
            "processing_time_ms": round(self.processing_time_ms, 2),
        }
