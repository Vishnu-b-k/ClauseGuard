# Deployment Guide

This repository is currently safe to deploy only in local mock mode. `APP_ENV`
values of `staging` and `production` reject `MOCK_MODE=true` at startup so a
mock contract-review service cannot be deployed by accident.

## 1. Prepare real services

Before creating a staging environment, implement the real Qdrant and ADK
adapters behind `src/bootstrap.py`. Provision:

- a managed Qdrant collection for legal evidence and policy documents;
- a PostgreSQL database for contracts, findings, review decisions, and audits;
- private object storage for uploaded contracts;
- a queue and worker service for asynchronous processing;
- a secrets manager for all provider keys and database credentials.

The API currently fails closed when `MOCK_MODE=false` because these adapters
are deliberately not implemented yet.

## 2. Configure the API

Copy `.env.example` to a local `.env` file for development. In staging and
production, set environment variables through the deployment platform rather
than committing them to source control:

```text
APP_ENV=production
MOCK_MODE=false
CORS_ALLOW_ORIGINS=https://review.example.com
MAX_UPLOAD_SIZE_BYTES=26214400
UPLOAD_CHUNK_SIZE_BYTES=1048576
RETRIEVAL_TOP_K=5
CONFIDENCE_THRESHOLD=0.8
LOG_LEVEL=INFO
ENABLE_API_DOCS=false
```

`CORS_ALLOW_ORIGINS` must name the exact frontend domain. Wildcard origins
and mock mode are rejected outside development and test environments.

## 3. Build and run the API image

```bash
docker build -t legal-ai-api .
docker run --rm -p 8080:8080 --env-file .env legal-ai-api
```

Verify both endpoints before deployment:

```bash
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/ready
```

## 4. Deploy to Cloud Run

Use a dedicated service account with only the permissions required for secret
access, object storage, queue publishing, and database connectivity. Store
credentials in Secret Manager; do not pass them in container images or source
control. Cloud Run supports container deployments and continuous delivery from
source repositories. See <https://cloud.google.com/run/docs/deploying> and
<https://cloud.google.com/run/docs/configuring/services/secrets>.

Build and push the image to Artifact Registry, then deploy it with the Cloud
Run service port set to `8080`. Configure the Cloud SQL connection with a
bounded connection pool; Cloud Run instances can each open up to 100 Cloud SQL
connections. See <https://cloud.google.com/sql/docs/postgres/connect-run>.

## 5. Deploy the frontend

Deploy `frontend/` to Vercel and set:

```text
NEXT_PUBLIC_API_URL=https://api.example.com
```

This value is intentionally public and must be the API's HTTPS URL. All
secrets remain backend-only. See <https://vercel.com/docs/environment-variables>.

## 6. Release controls

1. Run unit, API, and frontend build checks in CI.
2. Deploy to staging and execute a real upload-to-review smoke test.
3. Require approval before production deployment.
4. Enable application logs, error alerts, backups, object-retention policies,
   and Qdrant access controls.
5. Do not release until the mock service adapters and placeholder human-review
   actions have been replaced.