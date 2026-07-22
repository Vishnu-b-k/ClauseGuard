"""
End-to-End verification test suite for the Legal AI backend (Phase 5).
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ingestion.document_parser import ingest
from src.models.schemas import RiskLevel
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval import get_retrieval_client

SAMPLE_CONTRACT = Path(__file__).parent.parent / "sample_data" / "sample_contract.txt"


class TestBackendAIEndToEnd(unittest.TestCase):
    def test_full_pipeline_mock_mode(self):
        """Verify full pipeline execution when MOCK_MODE=True."""
        self.assertTrue(SAMPLE_CONTRACT.exists(), "Sample contract not found")
        
        with patch("src.config.MOCK_MODE", True), \
             patch("src.retrieval.__init__.MOCK_MODE", True), \
             patch("src.agents.legal_intelligence_agent.MOCK_MODE", True), \
             patch("src.agents.redline_summary_agent.MOCK_MODE", True):
            text = ingest(str(SAMPLE_CONTRACT))
            retrieval_client = get_retrieval_client()
            orchestrator = LyzrWorkflowOrchestrator(retrieval_client=retrieval_client)
            
            result = orchestrator.run(text, contract_id="E2E-MOCK")
            
            # Zero schema validation errors and non-empty outputs
            self.assertGreater(result.clauses_processed, 0)
            self.assertEqual(len(result.findings), result.clauses_processed)
            self.assertGreater(len(result.policy_decisions), 0)
            
            # Check FR-106 rule: any clause with confidence < 0.8 or risk in (high, critical) MUST be in flagged_for_review
            for finding in result.findings:
                decision = next((d for d in result.policy_decisions if d.clause_id == finding.clause_id), None)
                final_risk = decision.final_risk_level if decision else finding.risk_level
                
                if finding.confidence < 0.8 or final_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                    self.assertIn(finding.clause_id, result.flagged_for_review)
            
            # Verify result.to_dict() serializes safely into pure JSON
            result_dict = result.to_dict()
            json_str = json.dumps(result_dict)
            self.assertIsInstance(json_str, str)
            parsed_back = json.loads(json_str)
            self.assertEqual(parsed_back["contract_id"], "E2E-MOCK")

    def test_full_pipeline_real_mode_with_mocked_llm_responses(self):
        """Verify full pipeline execution when MOCK_MODE=False using simulated LLM/Qdrant."""
        self.assertTrue(SAMPLE_CONTRACT.exists(), "Sample contract not found")
        
        fake_finding_json = json.dumps({
            "risk_level": "critical",
            "confidence": 0.75,
            "cited_evidence_ids": ["POL-01"],
            "policy_refs": ["POL-LIAB-01"],
            "rationale": "Simulated critical risk finding from real ADK flow."
        })
        fake_redline_json = json.dumps({
            "suggested_text": "Capped liability at 1x contract value.",
            "rationale": "Mitigated exposure.",
            "executive_summary": "Liability capped."
        })
        
        with patch("src.config.MOCK_MODE", False), \
             patch("src.retrieval.__init__.MOCK_MODE", False), \
             patch("src.agents.legal_intelligence_agent.MOCK_MODE", False), \
             patch("src.agents.redline_summary_agent.MOCK_MODE", False), \
             patch("src.agents.legal_intelligence_agent.GOOGLE_API_KEY", "test-key"), \
             patch("src.agents.redline_summary_agent.GOOGLE_API_KEY", "test-key"), \
             patch("src.agents.legal_intelligence_agent.LegalIntelligenceAgent._invoke_llm", return_value=fake_finding_json), \
             patch("src.agents.redline_summary_agent.RedlineSummaryAgent._invoke_llm", return_value=fake_redline_json):
            
            text = ingest(str(SAMPLE_CONTRACT))
            retrieval_client = get_retrieval_client()
            orchestrator = LyzrWorkflowOrchestrator(retrieval_client=retrieval_client)
            
            result = orchestrator.run(text, contract_id="E2E-REAL")
            
            self.assertGreater(result.clauses_processed, 0)
            self.assertGreater(len(result.flagged_for_review), 0)
            for finding in result.findings:
                self.assertEqual(finding.risk_level, RiskLevel.CRITICAL)
                self.assertEqual(finding.confidence, 0.75)
                self.assertIn(finding.clause_id, result.flagged_for_review)
            
            # Check serialization
            json_str = json.dumps(result.to_dict())
            self.assertIn("E2E-REAL", json_str)


if __name__ == "__main__":
    unittest.main()
