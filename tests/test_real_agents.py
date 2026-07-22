"""
Unit tests for real Google ADK agents and retry/repair logic (Phase 3).
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from src.agents.legal_intelligence_agent import LegalIntelligenceAgent
from src.agents.redline_summary_agent import RedlineSummaryAgent
from src.models.schemas import (
    AgentFinding,
    Clause,
    EvidenceSource,
    RedlineSuggestion,
    RetrievedEvidence,
    RiskLevel,
    SchemaValidationError,
)


class TestRealAgents(unittest.TestCase):
    def setUp(self):
        self.clause = Clause(
            contract_id="test-contract",
            text="The Contractor shall have unlimited and uncapped liability for all direct and indirect damages.",
            clause_id="C-101",
        )
        self.evidence = [
            RetrievedEvidence(
                source=EvidenceSource.POLICY,
                text="Unlimited liability is strictly prohibited without Legal review.",
                similarity_score=0.95,
                evidence_id="POL-01",
                metadata={"policy_id": "POL-LIAB-01"},
            )
        ]

    def test_mock_mode_true_returns_valid_structured_output(self):
        with patch("src.agents.legal_intelligence_agent.MOCK_MODE", True), \
             patch("src.agents.redline_summary_agent.MOCK_MODE", True):
            intel_agent = LegalIntelligenceAgent()
            finding = intel_agent.analyze(self.clause, self.evidence)
            self.assertIsInstance(finding, AgentFinding)
            self.assertEqual(finding.risk_level, RiskLevel.CRITICAL)

            redline_agent = RedlineSummaryAgent()
            redline = redline_agent.generate(self.clause, finding)
            self.assertIsInstance(redline, RedlineSuggestion)
            self.assertNotEqual(redline.suggested_text, self.clause.text)

    def test_real_mode_parses_json_into_agent_finding(self):
        fake_response_dict = {
            "risk_level": "high",
            "confidence": 0.88,
            "cited_evidence_ids": ["POL-01"],
            "policy_refs": ["POL-LIAB-01"],
            "rationale": "High risk due to broad indemnity terms."
        }
        with patch("src.agents.legal_intelligence_agent.MOCK_MODE", False), \
             patch("src.agents.legal_intelligence_agent.GOOGLE_API_KEY", "test-key"), \
             patch.object(LegalIntelligenceAgent, "_invoke_llm", return_value=json.dumps(fake_response_dict)) as mock_invoke:
            agent = LegalIntelligenceAgent()
            finding = agent.analyze(self.clause, self.evidence)
            mock_invoke.assert_called_once()
            self.assertEqual(finding.risk_level, RiskLevel.HIGH)
            self.assertEqual(finding.confidence, 0.88)
            self.assertEqual(finding.cited_evidence_ids, ["POL-01"])
            self.assertEqual(finding.policy_refs, ["POL-LIAB-01"])

    def test_real_mode_parses_json_into_redline_suggestion(self):
        finding = AgentFinding(
            clause_id="C-101",
            risk_level=RiskLevel.HIGH,
            confidence=0.9,
            rationale="High risk clause.",
            cited_evidence_ids=["POL-01"]
        )
        fake_redline_dict = {
            "suggested_text": "The Contractor liability shall be capped at fees paid in the prior 12 months.",
            "rationale": "Capped liability to align with policy.",
            "executive_summary": "Liability capped to 12 months fees."
        }
        with patch("src.agents.redline_summary_agent.MOCK_MODE", False), \
             patch("src.agents.redline_summary_agent.GOOGLE_API_KEY", "test-key"), \
             patch.object(RedlineSummaryAgent, "_invoke_llm", return_value=json.dumps(fake_redline_dict)) as mock_invoke:
            agent = RedlineSummaryAgent()
            redline = agent.generate(self.clause, finding)
            mock_invoke.assert_called_once()
            self.assertEqual(redline.suggested_text, fake_redline_dict["suggested_text"])
            self.assertEqual(redline.rationale, fake_redline_dict["rationale"])

    def test_tenacity_retries_on_timeout_error(self):
        mock_response = MagicMock()
        mock_response.text = '{"risk_level": "medium", "confidence": 0.85, "cited_evidence_ids": ["POL-01"], "rationale": "Medium risk."}'
        
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = [
            TimeoutError("First timeout"),
            TimeoutError("Second timeout"),
            mock_response
        ]

        with patch("src.agents.legal_intelligence_agent.MOCK_MODE", False), \
             patch("src.agents.legal_intelligence_agent.GOOGLE_API_KEY", "test-key"), \
             patch("src.agents.legal_intelligence_agent.genai.Client", return_value=mock_client_instance):
            agent = LegalIntelligenceAgent()
            finding = agent.analyze(self.clause, self.evidence)
            self.assertEqual(mock_client_instance.models.generate_content.call_count, 3)
            self.assertEqual(finding.risk_level, RiskLevel.MEDIUM)

    def test_malformed_json_raises_schema_validation_error(self):
        with patch("src.agents.legal_intelligence_agent.MOCK_MODE", False), \
             patch("src.agents.legal_intelligence_agent.GOOGLE_API_KEY", "test-key"), \
             patch.object(LegalIntelligenceAgent, "_invoke_llm", return_value="Not valid JSON at all!"):
            agent = LegalIntelligenceAgent()
            with self.assertRaises(SchemaValidationError):
                agent.analyze(self.clause, self.evidence)


if __name__ == "__main__":
    unittest.main()
