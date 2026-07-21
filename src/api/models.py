"""Pydantic models for the FastAPI boundary."""

from typing import List
from pydantic import BaseModel


class AgentFindingResponse(BaseModel):
    clause_id: str
    risk_level: str
    confidence: float
    rationale: str
    cited_evidence_ids: List[str]
    policy_refs: List[str]


class RedlineSuggestionResponse(BaseModel):
    clause_id: str
    original_text: str
    suggested_text: str
    rationale: str
    executive_summary: str


class PolicyRuleResultResponse(BaseModel):
    rule_id: str
    description: str
    action: str


class PolicyDecisionResponse(BaseModel):
    finding_id: str
    clause_id: str
    original_risk_level: str
    original_confidence: float
    final_risk_level: str
    requires_human_review: bool
    rules_fired: List[PolicyRuleResultResponse]
    decision_id: str


class PipelineResultResponse(BaseModel):
    contract_id: str
    clauses_processed: int
    findings: List[AgentFindingResponse]
    redlines: List[RedlineSuggestionResponse]
    flagged_for_review: List[str]
    policy_decisions: List[PolicyDecisionResponse]
    warnings: List[str]
    processing_time_ms: float
