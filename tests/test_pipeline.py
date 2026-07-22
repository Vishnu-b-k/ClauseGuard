"""
Tests for the core pipeline. Uses stdlib unittest (no pytest dependency)
so this runs with just `python3 -m unittest discover`.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.agents.legal_intelligence_agent import LegalIntelligenceAgent
from src.ingestion.clause_segmenter import segment_into_clauses
from src.ingestion.document_parser import ingest
from src.models.schemas import Clause, RiskLevel
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval.qdrant_mock import MockQdrantRetrievalClient

SAMPLE_CONTRACT = Path(__file__).parent.parent / "sample_data" / "sample_contract.txt"


class TestClauseSegmenter(unittest.TestCase):
    def test_segments_numbered_contract_into_multiple_clauses(self):
        text = SAMPLE_CONTRACT.read_text()
        clauses = segment_into_clauses(text, contract_id="test-contract")
        self.assertGreaterEqual(len(clauses), 8)  # sample has 9 numbered sections
        for clause in clauses:
            self.assertTrue(clause.text.strip())

    def test_falls_back_to_paragraph_split_when_unnumbered(self):
        text = "First paragraph about payment terms.\n\nSecond paragraph about liability caps."
        clauses = segment_into_clauses(text, contract_id="unnumbered")
        self.assertEqual(len(clauses), 2)


class TestRetrieval(unittest.TestCase):
    def test_retrieve_returns_ranked_results_within_top_k(self):
        client = MockQdrantRetrievalClient()
        results = client.retrieve("unlimited liability without limitation", top_k=3)
        self.assertLessEqual(len(results), 3)
        self.assertTrue(results, "expected at least one match for a liability query")
        scores = [r.similarity_score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_retrieve_handles_no_match_gracefully(self):
        client = MockQdrantRetrievalClient()
        results = client.retrieve("xyzxyz nonsense query zzz", top_k=5)
        self.assertEqual(results, [])


from unittest.mock import patch

@patch("src.config.MOCK_MODE", True)
@patch("src.retrieval.__init__.MOCK_MODE", True)
@patch("src.agents.legal_intelligence_agent.MOCK_MODE", True)
@patch("src.agents.redline_summary_agent.MOCK_MODE", True)
class TestLegalIntelligenceAgent(unittest.TestCase):
    def setUp(self):
        self.agent = LegalIntelligenceAgent()
        self.retrieval = MockQdrantRetrievalClient()

    def test_unlimited_liability_language_scores_critical(self):
        clause = Clause(
            contract_id="unit-test",
            text="Provider's liability shall be unlimited liability for any "
            "and all damages, without limitation.",
        )
        evidence = self.retrieval.retrieve(clause.text, top_k=3)
        finding = self.agent.analyze(clause, evidence)

        self.assertEqual(finding.risk_level, RiskLevel.CRITICAL)
        self.assertTrue(finding.cited_evidence_ids)

    def test_bland_clause_scores_low(self):
        clause = Clause(
            contract_id="unit-test",
            text="Client shall pay all undisputed invoices within thirty "
            "(30) days of receipt.",
        )
        evidence = self.retrieval.retrieve(clause.text, top_k=3)
        finding = self.agent.analyze(clause, evidence)

        self.assertEqual(finding.risk_level, RiskLevel.LOW)

    def test_finding_without_evidence_has_capped_confidence(self):
        clause = Clause(contract_id="unit-test", text="Some entirely generic clause text.")
        finding = self.agent.analyze(clause, evidence=[])

        self.assertLessEqual(finding.confidence, 0.55)

    def test_finding_matches_across_newlines(self):
        clause = Clause(
            contract_id="unit-test",
            text="Provider will indemnify Client for any and all claims\nregardless\nof\ncause."
        )
        evidence = self.retrieval.retrieve(clause.text, top_k=3)
        finding = self.agent.analyze(clause, evidence)

        self.assertEqual(finding.risk_level, RiskLevel.HIGH)


@patch("src.config.MOCK_MODE", True)
@patch("src.retrieval.__init__.MOCK_MODE", True)
@patch("src.agents.legal_intelligence_agent.MOCK_MODE", True)
@patch("src.agents.redline_summary_agent.MOCK_MODE", True)
class TestOrchestratorEndToEnd(unittest.TestCase):
    def setUp(self):
        self.orchestrator = LyzrWorkflowOrchestrator(
            retrieval_client=MockQdrantRetrievalClient()
        )

    def test_full_pipeline_runs_on_sample_contract(self):
        text = ingest(str(SAMPLE_CONTRACT))
        result = self.orchestrator.run(text, contract_id="sample-contract")

        self.assertGreater(result.clauses_processed, 0)
        self.assertEqual(len(result.findings), result.clauses_processed)
        self.assertGreater(result.processing_time_ms, 0)
        # FR-106: every successful finding gets a policy decision
        self.assertEqual(len(result.policy_decisions), len(result.findings))

    def test_at_least_one_critical_finding_on_sample_contract(self):
        # Pipeline-level: the sample contract's liability clause should
        # surface as CRITICAL somewhere in the aggregate results. Checked
        # at this level (not by matching a specific clause_id back to
        # source text) because clause_id is randomly generated per
        # segmentation call and isn't meant to be stable across calls.
        text = ingest(str(SAMPLE_CONTRACT))
        result = self.orchestrator.run(text, contract_id="sample-contract")

        risk_levels = [f.risk_level for f in result.findings]
        self.assertIn(RiskLevel.CRITICAL, risk_levels)

    def test_high_risk_clauses_get_redlines(self):
        text = ingest(str(SAMPLE_CONTRACT))
        result = self.orchestrator.run(text, contract_id="sample-contract")
        self.assertGreater(len(result.redlines), 0, "expected at least one redline on the sample contract")

    def test_low_confidence_or_high_risk_clauses_are_flagged_for_review(self):
        text = ingest(str(SAMPLE_CONTRACT))
        result = self.orchestrator.run(text, contract_id="sample-contract")
        self.assertGreater(len(result.flagged_for_review), 0)

    def test_result_serializes_to_json_safely(self):
        import json
        text = ingest(str(SAMPLE_CONTRACT))
        result = self.orchestrator.run(text, contract_id="sample-contract")
        serialized = json.dumps(result.to_dict())
        self.assertIn("sample-contract", serialized)
        self.assertIn("policy_decisions", serialized)


if __name__ == "__main__":
    unittest.main()
