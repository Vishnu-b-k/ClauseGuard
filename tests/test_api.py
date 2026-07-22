import os
import unittest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)
SAMPLE_CONTRACT = Path(__file__).parent.parent / "sample_data" / "sample_contract.txt"


from unittest.mock import patch

@patch("src.config.MOCK_MODE", True)
@patch("src.retrieval.__init__.MOCK_MODE", True)
@patch("src.agents.legal_intelligence_agent.MOCK_MODE", True)
@patch("src.agents.redline_summary_agent.MOCK_MODE", True)
class TestAPI(unittest.TestCase):
    def test_health(self):
        response = client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        
    def test_analyze_contract_success(self):
        self.assertTrue(SAMPLE_CONTRACT.exists(), "Sample contract not found")
        
        with open(SAMPLE_CONTRACT, "rb") as f:
            response = client.post(
                "/api/v1/contracts/analyze",
                files={"file": ("sample_contract.txt", f, "text/plain")}
            )
            
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("findings", data)
        self.assertIn("redlines", data)
        self.assertIn("policy_decisions", data)
        
        self.assertGreater(len(data["findings"]), 0)
        self.assertGreater(len(data["policy_decisions"]), 0)
        
    def test_analyze_contract_invalid_file_type(self):
        # We simulate a file extension that is not in the allowed list (.exe)
        fd, path = tempfile.mkstemp(suffix=".exe")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(b"MZ1234")
            with open(path, "rb") as f:
                response = client.post(
                    "/api/v1/contracts/analyze",
                    files={"file": ("malicious.exe", f, "application/octet-stream")}
                )
            
            # Should be 400 Bad Request from IngestionValidationError
            self.assertEqual(response.status_code, 400)
            self.assertIn("Unsupported file type", response.json()["detail"])
        finally:
            if os.path.exists(path):
                os.remove(path)
                
    def test_analyze_contract_empty_file(self):
        # We simulate an empty txt file
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(b"")
            with open(path, "rb") as f:
                response = client.post(
                    "/api/v1/contracts/analyze",
                    files={"file": ("empty.txt", f, "text/plain")}
                )
            
            self.assertEqual(response.status_code, 400)
            self.assertIn("File is empty", response.json()["detail"])
        finally:
            if os.path.exists(path):
                os.remove(path)

if __name__ == "__main__":
    unittest.main()
