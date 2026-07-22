"""
Unit tests for Qdrant Cloud client and factory fallback (Phase 2).
"""

import os
import unittest
from unittest.mock import patch

from src.models.schemas import EvidenceSource, RetrievedEvidence
from src.retrieval import get_retrieval_client
from src.retrieval.qdrant_mock import MockQdrantRetrievalClient
from src.retrieval.qdrant_client import RealQdrantRetrievalClient


class TestQdrantClient(unittest.TestCase):
    def test_factory_returns_mock_when_mock_mode_true(self):
        with patch("src.retrieval.MOCK_MODE", True):
            client = get_retrieval_client()
            self.assertIsInstance(client, MockQdrantRetrievalClient)

    def test_factory_returns_mock_when_url_empty(self):
        with patch("src.retrieval.MOCK_MODE", False), patch("src.retrieval.QDRANT_URL", ""):
            client = get_retrieval_client()
            self.assertIsInstance(client, MockQdrantRetrievalClient)

    def test_factory_falls_back_to_mock_on_connection_error(self):
        with patch("src.retrieval.MOCK_MODE", False), \
             patch("src.retrieval.QDRANT_URL", "https://invalid-qdrant.local:6333"), \
             patch("src.retrieval.RealQdrantRetrievalClient", side_effect=Exception("Connection refused")):
            client = get_retrieval_client()
            self.assertIsInstance(client, MockQdrantRetrievalClient)

    def test_real_client_in_memory_seeding_and_retrieval(self):
        client = RealQdrantRetrievalClient(url=":memory:")
        results = client.retrieve("unlimited liability", top_k=3)
        self.assertGreaterEqual(len(results), 1)
        self.assertLessEqual(len(results), 3)
        for ev in results:
            self.assertIsInstance(ev, RetrievedEvidence)
            self.assertIn(ev.source, [EvidenceSource.POLICY, EvidenceSource.STANDARD_CLAUSE])
            self.assertGreaterEqual(ev.similarity_score, 0.0)
            self.assertLessEqual(ev.similarity_score, 1.0)
            self.assertTrue(ev.text)

    def test_real_client_empty_query_returns_empty(self):
        client = RealQdrantRetrievalClient(url=":memory:")
        self.assertEqual(client.retrieve("   "), [])
        self.assertEqual(client.retrieve(""), [])


if __name__ == "__main__":
    unittest.main()
