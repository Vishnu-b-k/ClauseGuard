"""
Unit tests for Phase 4 async FastAPI enhancements (`src/api/app.py`).
"""

import io
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)
SAMPLE_CONTRACT = Path(__file__).parent.parent / "sample_data" / "sample_contract.txt"


@patch("src.config.MOCK_MODE", True)
@patch("src.retrieval.__init__.MOCK_MODE", True)
@patch("src.agents.legal_intelligence_agent.MOCK_MODE", True)
@patch("src.agents.redline_summary_agent.MOCK_MODE", True)
class TestFastAPIAsync(unittest.TestCase):
    def test_async_analyze_works_with_valid_txt_and_returns_correlation_id(self):
        self.assertTrue(SAMPLE_CONTRACT.exists(), "Sample contract not found")
        
        with open(SAMPLE_CONTRACT, "rb") as f:
            response = client.post(
                "/api/v1/contracts/analyze",
                files={"file": ("sample_contract.txt", f, "text/plain")},
                headers={"X-Correlation-ID": "test-correlation-123"}
            )
            
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Correlation-ID"), "test-correlation-123")
        
        data = response.json()
        self.assertIn("contract_id", data)
        self.assertIn("clauses_processed", data)
        self.assertIn("findings", data)
        self.assertIn("redlines", data)
        self.assertIn("flagged_for_review", data)
        self.assertIn("policy_decisions", data)
        self.assertIn("warnings", data)
        self.assertIn("processing_time_ms", data)

    def test_auto_generates_correlation_id_when_missing(self):
        with open(SAMPLE_CONTRACT, "rb") as f:
            response = client.post(
                "/api/v1/contracts/analyze",
                files={"file": ("sample_contract.txt", f, "text/plain")}
            )
        self.assertEqual(response.status_code, 200)
        corr_id = response.headers.get("X-Correlation-ID")
        self.assertIsNotNone(corr_id)
        self.assertGreater(len(corr_id), 10)  # UUID4 shape check

    def test_returns_http_400_for_invalid_file_extension(self):
        dummy_content = b"Some binary or invalid content"
        response = client.post(
            "/api/v1/contracts/analyze",
            files={"file": ("bad_file.bin", io.BytesIO(dummy_content), "application/octet-stream")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])

    def test_returns_http_413_for_oversized_payloads(self):
        # We patch MAX_FILE_SIZE_BYTES to 100 bytes to quickly test the 413 guard
        with patch("src.api.app.MAX_FILE_SIZE_BYTES", 100):
            large_content = b"A" * 200
            response = client.post(
                "/api/v1/contracts/analyze",
                files={"file": ("oversized.txt", io.BytesIO(large_content), "text/plain")}
            )
            self.assertEqual(response.status_code, 413)
            self.assertIn("File too large", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
