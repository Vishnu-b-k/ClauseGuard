"""Tests for runtime configuration and deployment-facing API safeguards."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config import ConfigurationError, load_settings


class TestRuntimeSettings(unittest.TestCase):
    def test_development_defaults_are_safe_for_local_frontend(self):
        settings = load_settings({})
        self.assertEqual(settings.environment, "development")
        self.assertTrue(settings.mock_mode)
        self.assertEqual(settings.allowed_origins, ("http://localhost:3000",))

    def test_production_rejects_mock_services(self):
        with self.assertRaises(ConfigurationError):
            load_settings({"APP_ENV": "production", "MOCK_MODE": "true"})

    def test_production_rejects_wildcard_cors(self):
        with self.assertRaises(ConfigurationError):
            load_settings(
                {
                    "APP_ENV": "production",
                    "MOCK_MODE": "false",
                    "CORS_ALLOW_ORIGINS": "*",
                }
            )

    def test_production_allows_explicit_origins_with_real_services(self):
        settings = load_settings(
            {
                "APP_ENV": "production",
                "MOCK_MODE": "false",
                "CORS_ALLOW_ORIGINS": "https://review.example.com",
                "ENABLE_API_DOCS": "false",
            }
        )
        self.assertFalse(settings.mock_mode)
        self.assertFalse(settings.enable_docs)

    def test_upload_chunk_cannot_exceed_upload_limit(self):
        with self.assertRaises(ConfigurationError):
            load_settings(
                {
                    "MAX_UPLOAD_SIZE_BYTES": "4",
                    "UPLOAD_CHUNK_SIZE_BYTES": "5",
                }
            )


class TestDeploymentApiSafeguards(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings(
            {
                "APP_ENV": "test",
                "MOCK_MODE": "true",
                "CORS_ALLOW_ORIGINS": "https://review.example.com",
                "MAX_UPLOAD_SIZE_BYTES": "4",
                "UPLOAD_CHUNK_SIZE_BYTES": "2",
                "ENABLE_API_DOCS": "false",
            }
        )
        self.client = TestClient(create_app(self.settings))

    def test_readiness_reports_configured_environment(self):
        response = self.client.get("/api/v1/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "environment": "test"})

    def test_cors_allows_only_the_configured_origin(self):
        response = self.client.options(
            "/api/v1/contracts/analyze",
            headers={
                "Origin": "https://review.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "https://review.example.com",
        )

    def test_oversized_upload_is_rejected(self):
        response = self.client.post(
            "/api/v1/contracts/analyze",
            files={"file": ("too-large.txt", b"12345", "text/plain")},
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("maximum upload size", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()