"""
Tests for the Deterministic Policy Validator (FR-106).
Uses stdlib unittest, same style as tests/test_pipeline.py.

Each test class targets one specific policy rule, plus integration tests
for combined-rule scenarios and explainability requirements.
"""

from __future__ import annotations

import json
import unittest

from src.models.schemas import (
    AgentFinding,
    PolicyDecision,
    RiskLevel,
    SchemaValidationError,
)
from pydantic import ValidationError
from src.rules.deterministic_policy_validator import DeterministicPolicyValidator


def _make_finding(
    risk_level: RiskLevel = RiskLevel.LOW,
    confidence: float = 0.90,
    policy_refs: list[str] | None = None,
    clause_id: str = "C-test",
) -> AgentFinding:
    """Helper to build a minimal valid AgentFinding for rule-engine tests."""
    return AgentFinding(
        clause_id=clause_id,
        risk_level=risk_level,
        confidence=confidence,
        rationale="Test rationale for unit testing.",
        cited_evidence_ids=["EV-test-001"],
        policy_refs=policy_refs or [],
    )


class TestCriticalReviewRule(unittest.TestCase):
    """POL-CRIT-REVIEW: critical findings always require human review."""

    def setUp(self):
        self.validator = DeterministicPolicyValidator()

    def test_critical_finding_requires_review(self):
        finding = _make_finding(risk_level=RiskLevel.CRITICAL, confidence=0.99)
        decision = self.validator.validate(finding)
        self.assertTrue(decision.requires_human_review)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertIn("POL-CRIT-REVIEW", rule_ids)

    def test_critical_finding_stays_critical(self):
        finding = _make_finding(risk_level=RiskLevel.CRITICAL, confidence=0.99)
        decision = self.validator.validate(finding)
        self.assertEqual(decision.final_risk_level, RiskLevel.CRITICAL)


class TestHighReviewRule(unittest.TestCase):
    """POL-HIGH-REVIEW: high-risk findings always require human review."""

    def setUp(self):
        self.validator = DeterministicPolicyValidator()

    def test_high_finding_requires_review(self):
        finding = _make_finding(risk_level=RiskLevel.HIGH, confidence=0.95)
        decision = self.validator.validate(finding)
        self.assertTrue(decision.requires_human_review)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertIn("POL-HIGH-REVIEW", rule_ids)


class TestConfidenceThresholdRule(unittest.TestCase):
    """POL-CONF-REVIEW: confidence < 0.8 always requires human review."""

    def setUp(self):
        self.validator = DeterministicPolicyValidator()

    def test_low_confidence_requires_review(self):
        finding = _make_finding(risk_level=RiskLevel.LOW, confidence=0.55)
        decision = self.validator.validate(finding)
        self.assertTrue(decision.requires_human_review)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertIn("POL-CONF-REVIEW", rule_ids)

    def test_borderline_confidence_requires_review(self):
        """0.79 is below the 0.8 threshold -- must trigger."""
        finding = _make_finding(risk_level=RiskLevel.LOW, confidence=0.79)
        decision = self.validator.validate(finding)
        self.assertTrue(decision.requires_human_review)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertIn("POL-CONF-REVIEW", rule_ids)

    def test_at_threshold_does_not_trigger(self):
        """0.80 is AT the threshold -- should NOT trigger (< 0.8, not <=)."""
        finding = _make_finding(risk_level=RiskLevel.LOW, confidence=0.80)
        decision = self.validator.validate(finding)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertNotIn("POL-CONF-REVIEW", rule_ids)

    def test_above_threshold_does_not_trigger(self):
        finding = _make_finding(risk_level=RiskLevel.LOW, confidence=0.95)
        decision = self.validator.validate(finding)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertNotIn("POL-CONF-REVIEW", rule_ids)


class TestPolicyEscalationRule(unittest.TestCase):
    """POL-ESCALATE-001: policy_refs non-empty escalates risk by one step
    if not already high or critical."""

    def setUp(self):
        self.validator = DeterministicPolicyValidator()

    def test_low_with_policy_refs_escalates_to_medium(self):
        finding = _make_finding(
            risk_level=RiskLevel.LOW,
            confidence=0.90,
            policy_refs=["POL-LIAB-01"],
        )
        decision = self.validator.validate(finding)
        self.assertEqual(decision.original_risk_level, RiskLevel.LOW)
        self.assertEqual(decision.final_risk_level, RiskLevel.MEDIUM)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertIn("POL-ESCALATE-001", rule_ids)

    def test_medium_with_policy_refs_escalates_to_high(self):
        finding = _make_finding(
            risk_level=RiskLevel.MEDIUM,
            confidence=0.90,
            policy_refs=["POL-TERM-03"],
        )
        decision = self.validator.validate(finding)
        self.assertEqual(decision.original_risk_level, RiskLevel.MEDIUM)
        self.assertEqual(decision.final_risk_level, RiskLevel.HIGH)
        # Escalated to HIGH, so POL-HIGH-REVIEW should also fire
        self.assertTrue(decision.requires_human_review)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertIn("POL-ESCALATE-001", rule_ids)
        self.assertIn("POL-HIGH-REVIEW", rule_ids)

    def test_high_with_policy_refs_does_not_escalate(self):
        finding = _make_finding(
            risk_level=RiskLevel.HIGH,
            confidence=0.90,
            policy_refs=["POL-INDEM-04"],
        )
        decision = self.validator.validate(finding)
        self.assertEqual(decision.final_risk_level, RiskLevel.HIGH)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertNotIn("POL-ESCALATE-001", rule_ids)

    def test_critical_with_policy_refs_does_not_escalate(self):
        finding = _make_finding(
            risk_level=RiskLevel.CRITICAL,
            confidence=0.90,
            policy_refs=["POL-LIAB-01"],
        )
        decision = self.validator.validate(finding)
        self.assertEqual(decision.final_risk_level, RiskLevel.CRITICAL)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertNotIn("POL-ESCALATE-001", rule_ids)

    def test_no_policy_refs_does_not_escalate(self):
        finding = _make_finding(
            risk_level=RiskLevel.LOW,
            confidence=0.90,
            policy_refs=[],
        )
        decision = self.validator.validate(finding)
        self.assertEqual(decision.final_risk_level, RiskLevel.LOW)
        rule_ids = [r.rule_id for r in decision.rules_fired]
        self.assertNotIn("POL-ESCALATE-001", rule_ids)


class TestCleanClausePassesThrough(unittest.TestCase):
    """A clean, high-confidence clause with no policy refs should pass
    through without review or escalation."""

    def setUp(self):
        self.validator = DeterministicPolicyValidator()

    def test_clean_clause_not_flagged(self):
        finding = _make_finding(
            risk_level=RiskLevel.LOW,
            confidence=0.95,
            policy_refs=[],
        )
        decision = self.validator.validate(finding)
        self.assertFalse(decision.requires_human_review)
        self.assertEqual(decision.final_risk_level, RiskLevel.LOW)
        self.assertEqual(len(decision.rules_fired), 0)


class TestExplainabilityAuditTrail(unittest.TestCase):
    """AI Governance / Explainability: every decision carries a reasoning
    trail -- which specific rules fired and why."""

    def setUp(self):
        self.validator = DeterministicPolicyValidator()

    def test_rules_fired_has_id_description_action(self):
        finding = _make_finding(risk_level=RiskLevel.CRITICAL, confidence=0.50)
        decision = self.validator.validate(finding)
        self.assertGreater(len(decision.rules_fired), 0)
        for rule_result in decision.rules_fired:
            self.assertTrue(rule_result.rule_id, "rule_id must not be empty")
            self.assertTrue(rule_result.description, "description must not be empty")
            self.assertTrue(rule_result.action, "action must not be empty")

    def test_decision_serializes_to_json_with_rules(self):
        finding = _make_finding(
            risk_level=RiskLevel.MEDIUM,
            confidence=0.50,
            policy_refs=["POL-LIAB-01"],
        )
        decision = self.validator.validate(finding)
        serialized = json.dumps(decision.to_dict())
        self.assertIn("POL-ESCALATE-001", serialized)
        self.assertIn("POL-CONF-REVIEW", serialized)
        # Escalated medium -> high, so also has high review
        self.assertIn("POL-HIGH-REVIEW", serialized)


class TestPolicyDecisionValidation(unittest.TestCase):
    """PolicyDecision.validate() rejects impossible states."""

    def test_final_risk_below_original_raises(self):
        with self.assertRaises(ValidationError):
            PolicyDecision(
                finding_id="F-test",
                clause_id="C-test",
                original_risk_level=RiskLevel.HIGH,
                original_confidence=0.90,
                final_risk_level=RiskLevel.LOW,  # invalid: can't go down
                requires_human_review=False,
            )

    def test_same_risk_level_passes_validation(self):
        decision = PolicyDecision(
            finding_id="F-test",
            clause_id="C-test",
            original_risk_level=RiskLevel.LOW,
            original_confidence=0.90,
            final_risk_level=RiskLevel.LOW,
            requires_human_review=False,
        )
        decision.validate()  # should not raise


class TestCombinedRules(unittest.TestCase):
    """Multiple rules can fire on the same finding."""

    def setUp(self):
        self.validator = DeterministicPolicyValidator()

    def test_critical_and_low_confidence_fires_both(self):
        finding = _make_finding(risk_level=RiskLevel.CRITICAL, confidence=0.50)
        decision = self.validator.validate(finding)
        self.assertTrue(decision.requires_human_review)
        rule_ids = {r.rule_id for r in decision.rules_fired}
        self.assertIn("POL-CRIT-REVIEW", rule_ids)
        self.assertIn("POL-CONF-REVIEW", rule_ids)

    def test_medium_with_policy_refs_and_low_confidence(self):
        """Escalation + confidence review + high review should all fire."""
        finding = _make_finding(
            risk_level=RiskLevel.MEDIUM,
            confidence=0.50,
            policy_refs=["POL-TERM-03"],
        )
        decision = self.validator.validate(finding)
        self.assertEqual(decision.final_risk_level, RiskLevel.HIGH)
        self.assertTrue(decision.requires_human_review)
        rule_ids = {r.rule_id for r in decision.rules_fired}
        self.assertIn("POL-ESCALATE-001", rule_ids)
        self.assertIn("POL-HIGH-REVIEW", rule_ids)
        self.assertIn("POL-CONF-REVIEW", rule_ids)


if __name__ == "__main__":
    unittest.main()
