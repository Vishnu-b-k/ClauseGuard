"""
Deterministic Policy Validator (FR-106).

PRD: "Apply hardcoded business rules to AI findings to calculate risk
scores."  Acceptance criteria: "High-risk or low-confidence findings are
routed to the Human Review Workspace."

Architecture: sits in the "Intelligence & Rules Layer" zone between the
AI agents' output and the orchestrator's final review/redline decisions.
Tagged tech stack: Python, JSON Rules Engine, Confidence-Based Routing
Logic.

Design principles:
  - Data-driven, declarative rule set -- not scattered if/else logic.
    A compliance reviewer should be able to read POLICY_RULES as a
    plain-language policy table without reading Python.
  - Every decision carries a full reasoning trail (rules_fired) per
    the PRD's AI Governance / Explainability requirement.
  - This is the component that stops the pipeline from trusting AI
    judgment alone.
"""

from __future__ import annotations

from src.config import CONFIDENCE_THRESHOLD
from src.models.schemas import (
    AgentFinding,
    PolicyDecision,
    PolicyRuleResult,
    RiskLevel,
)


# -- Helpers ---------------------------------------------------------------

_RISK_LADDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


def _escalate_risk(current: RiskLevel, steps: int = 1) -> RiskLevel:
    """Move a risk level up by ``steps`` on the LOW -> MEDIUM -> HIGH ->
    CRITICAL ladder, capped at CRITICAL."""
    idx = _RISK_LADDER.index(current)
    return _RISK_LADDER[min(idx + steps, len(_RISK_LADDER) - 1)]


# -- Declarative Policy Rule Table -----------------------------------------
#
# Each rule is a dict with:
#   rule_id       - stable identifier for audit trails
#   description   - plain-English explanation a compliance reviewer can read
#   prd_ref       - which PRD requirement / section this rule enforces
#   phase         - "escalation" (runs first, may change risk level)
#                   or "review" (runs second, uses final risk level)
#   condition     - callable(finding, current_risk_level) -> bool
#   flag_review   - if True and condition fires, set requires_human_review
#   escalate_by   - if > 0 and condition fires, bump final risk by N steps
#
# +---------------------+-----------+-------------+-------------------------------+
# | Rule ID             | Phase     | Action      | Condition (plain English)     |
# +---------------------+-----------+-------------+-------------------------------+
# | POL-ESCALATE-001    | escalation| escalate +1 | policy_refs non-empty AND     |
# |                     |           |             | risk < high                   |
# | POL-CRIT-REVIEW     | review    | flag review | final risk == critical        |
# | POL-HIGH-REVIEW     | review    | flag review | final risk == high            |
# | POL-CONF-REVIEW     | review    | flag review | confidence < 0.8             |
# +---------------------+-----------+-------------+-------------------------------+

POLICY_RULES: list[dict] = [
    # -- Phase 1: Escalation rules (adjust risk level before review decisions) --
    {
        "rule_id": "POL-ESCALATE-001",
        "description": (
            "Findings matched against a named corporate policy (non-empty "
            "policy_refs from the retrieval layer) have their risk level "
            "escalated by one step if not already high or critical, reflecting "
            "that policy-relevant clauses warrant elevated scrutiny."
        ),
        "prd_ref": "FR-106: Deterministic Policy Validation; FR-103 policy grounding",
        "phase": "escalation",
        "condition": lambda finding, risk: (
            bool(finding.policy_refs)
            and risk not in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        ),
        "flag_review": False,
        "escalate_by": 1,
    },
    # -- Phase 2: Review-trigger rules (evaluated against final risk level) --
    {
        "rule_id": "POL-CRIT-REVIEW",
        "description": (
            "Critical-risk findings always require human review, regardless "
            "of confidence score."
        ),
        "prd_ref": "FR-106 AC: High-risk or low-confidence findings routed to Human Review",
        "phase": "review",
        "condition": lambda finding, risk: risk == RiskLevel.CRITICAL,
        "flag_review": True,
        "escalate_by": 0,
    },
    {
        "rule_id": "POL-HIGH-REVIEW",
        "description": (
            "High-risk findings always require human review, regardless "
            "of confidence score."
        ),
        "prd_ref": "FR-106 AC: High-risk or low-confidence findings routed to Human Review",
        "phase": "review",
        "condition": lambda finding, risk: risk == RiskLevel.HIGH,
        "flag_review": True,
        "escalate_by": 0,
    },
    {
        "rule_id": "POL-CONF-REVIEW",
        "description": (
            f"Findings with confidence below the governance threshold "
            f"({CONFIDENCE_THRESHOLD}) always require human review, "
            f"regardless of risk level."
        ),
        "prd_ref": (
            "AI Governance / Confidence Thresholds: "
            f"scores < {CONFIDENCE_THRESHOLD} trigger mandatory human review"
        ),
        "phase": "review",
        "condition": lambda finding, risk: finding.confidence < CONFIDENCE_THRESHOLD,
        "flag_review": True,
        "escalate_by": 0,
    },
]


class DeterministicPolicyValidator:
    """Deterministic Policy Validator (FR-106).

    Runs every AgentFinding through the full POLICY_RULES table and returns
    a PolicyDecision with:
    - final_risk_level (may be escalated from the AI's original)
    - requires_human_review (True if any review rule fired)
    - rules_fired (full audit trail of which rules triggered and what they did)
    """

    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules if rules is not None else POLICY_RULES

    def validate(self, finding: AgentFinding) -> PolicyDecision:
        """Run all policy rules against a finding and return the aggregate
        decision.

        Rules are evaluated in two phases:
        1. Escalation -- may raise final_risk_level above the AI's original.
        2. Review -- decides whether the clause needs human review, using
           the (possibly escalated) final risk level.

        Every rule that fires is recorded in rules_fired for explainability.
        """
        final_risk = finding.risk_level
        requires_review = False
        fired: list[PolicyRuleResult] = []

        for phase in ("escalation", "review"):
            for rule in self.rules:
                if rule["phase"] != phase:
                    continue
                if not rule["condition"](finding, final_risk):
                    continue

                old_risk = final_risk
                if rule["escalate_by"] > 0:
                    final_risk = _escalate_risk(final_risk, rule["escalate_by"])
                if rule["flag_review"]:
                    requires_review = True

                # Build human-readable action description for the audit trail
                parts: list[str] = []
                if rule["escalate_by"] > 0 and final_risk != old_risk:
                    parts.append(
                        f"Escalated risk from {old_risk.value} to {final_risk.value}"
                    )
                if rule["flag_review"]:
                    parts.append("Flagged for human review")

                fired.append(PolicyRuleResult(
                    rule_id=rule["rule_id"],
                    description=rule["description"],
                    action="; ".join(parts) or "Rule matched",
                ))

        decision = PolicyDecision(
            finding_id=finding.finding_id,
            clause_id=finding.clause_id,
            original_risk_level=finding.risk_level,
            original_confidence=finding.confidence,
            final_risk_level=final_risk,
            requires_human_review=requires_review,
            rules_fired=fired,
        )
        decision.validate()
        return decision
