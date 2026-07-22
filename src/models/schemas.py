"""
Core data contracts for the Legal AI Contract Compliance pipeline.

PRD traceability:
    FR-102  Clause Segmentation        -> Clause
    FR-103  Hybrid Retrieval (RAG)     -> RetrievedEvidence
    FR-104  Multi-Agent Reasoning      -> AgentFinding
    FR-105  Structured Output Validation -> validate() on every model below
    FR-107  Human-in-the-Loop Feedback -> PipelineResult.flagged_for_review

Production note: these are now Pydantic models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
import uuid

from pydantic import BaseModel, Field, model_validator


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


class Clause(BaseModel):
    """One segmented clause from a contract. Produced by
    src/ingestion/clause_segmenter.py (FR-102)."""

    contract_id: str
    text: str
    clause_id: str = Field(default_factory=lambda: _new_id("C"))
    clause_type_guess: Optional[str] = None  # e.g. "liability", "termination"
    start_offset: int = 0
    end_offset: int = 0

    @model_validator(mode='after')
    def validate_clause(self) -> 'Clause':
        if not self.text or not self.text.strip():
            raise SchemaValidationError(f"{self.clause_id}: clause text is empty")
        if self.end_offset < self.start_offset:
            raise SchemaValidationError(f"{self.clause_id}: invalid offsets")
        return self

    def validate(self) -> None:
        pass

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class RetrievedEvidence(BaseModel):
    """One hit from the Qdrant Hybrid Retrieval Engine (FR-103)."""

    source: EvidenceSource
    text: str
    similarity_score: float  # combined dense+sparse score, 0..1
    evidence_id: str = Field(default_factory=lambda: _new_id("EV"))
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_evidence(self) -> 'RetrievedEvidence':
        if not 0.0 <= self.similarity_score <= 1.0:
            raise SchemaValidationError(
                f"{self.evidence_id}: similarity_score {self.similarity_score} out of range"
            )
        if not self.text.strip():
            raise SchemaValidationError(f"{self.evidence_id}: evidence text is empty")
        return self

    def validate(self) -> None:
        pass

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class AgentFinding(BaseModel):
    """Structured output of the Legal Intelligence Agent (FR-104).
    This is the object the Deterministic Policy Validator would consume
    in the next sprint slice -- kept here so that hookup is a no-op."""

    clause_id: str
    risk_level: RiskLevel
    confidence: float  # 0..1 -- PRD AI Governance: <0.8 forces human review
    rationale: str
    cited_evidence_ids: List[str] = Field(default_factory=list)
    policy_refs: List[str] = Field(default_factory=list)
    finding_id: str = Field(default_factory=lambda: _new_id("F"))
    generated_at: str = Field(default_factory=_utcnow)

    @model_validator(mode='after')
    def validate_finding(self) -> 'AgentFinding':
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
        return self

    def validate(self) -> None:
        pass

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class RedlineSuggestion(BaseModel):
    """Structured output of the Redline & Summary Agent (FR-104)."""

    clause_id: str
    original_text: str
    suggested_text: str
    rationale: str
    executive_summary: str
    redline_id: str = Field(default_factory=lambda: _new_id("R"))

    @model_validator(mode='after')
    def validate_redline(self) -> 'RedlineSuggestion':
        if self.suggested_text.strip() == self.original_text.strip():
            raise SchemaValidationError(
                f"{self.redline_id}: suggested_text is identical to original"
            )
        if not self.rationale.strip():
            raise SchemaValidationError(f"{self.redline_id}: missing rationale")
        return self

    def validate(self) -> None:
        pass

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class PolicyRuleResult(BaseModel):
    """One policy rule that fired during deterministic validation (FR-106).
    Part of the AI Governance explainability requirement: every decision
    carries a reasoning trail of which specific rules fired and why."""

    rule_id: str
    description: str
    action: str  # human-readable summary of what the rule did

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class PolicyDecision(BaseModel):
    """Aggregate output of the Deterministic Policy Validator (FR-106).
    Wraps an AgentFinding with the validator's final, auditable determination.
    """

    finding_id: str
    clause_id: str
    original_risk_level: RiskLevel
    original_confidence: float
    final_risk_level: RiskLevel
    requires_human_review: bool
    rules_fired: List[PolicyRuleResult] = Field(default_factory=list)
    decision_id: str = Field(default_factory=lambda: _new_id("PD"))

    @model_validator(mode='after')
    def validate_decision(self) -> 'PolicyDecision':
        if RiskLevel.ordinal(self.final_risk_level) < RiskLevel.ordinal(self.original_risk_level):
            raise SchemaValidationError(
                f"{self.decision_id}: final risk level ({self.final_risk_level.value}) "
                f"cannot be lower than original ({self.original_risk_level.value})"
            )
        return self

    def validate(self) -> None:
        pass

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class PipelineResult(BaseModel):
    """Top-level aggregate returned by the Lyzr Orchestrator for one contract."""

    contract_id: str
    clauses_processed: int
    findings: List[AgentFinding] = Field(default_factory=list)
    redlines: List[RedlineSuggestion] = Field(default_factory=list)
    flagged_for_review: List[str] = Field(default_factory=list)  # clause_ids, FR-106/FR-107
    policy_decisions: List[PolicyDecision] = Field(default_factory=list)  # FR-106
    warnings: List[str] = Field(default_factory=list)
    all_clauses: List[Clause] = Field(default_factory=list)
    processing_time_ms: float = 0.0

    @model_validator(mode='after')
    def validate_pipeline(self) -> 'PipelineResult':
        if self.clauses_processed < 0:
            raise SchemaValidationError("clauses_processed cannot be negative")
        if len(self.findings) > self.clauses_processed:
            raise SchemaValidationError("more findings than clauses processed")
        return self

    def validate(self) -> None:
        pass

    def to_dict(self) -> dict:
        d = self.model_dump(mode="json")
        d["processing_time_ms"] = round(self.processing_time_ms, 2)
        return d
