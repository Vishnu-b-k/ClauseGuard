# Legal AI Contract Compliance Platform - Agent Knowledge Base

## Project Overview
The Legal AI Contract Compliance Platform is an enterprise-grade solution designed to automate the review, risk assessment, and redlining of legal contracts. It uses a dual-agent architecture (Google ADK / LLMs) combined with a Qdrant hybrid retrieval layer for grounding (RAG), coordinated by a Lyzr orchestrator. A Deterministic Policy Validator sits between the AI and the user to enforce hardcoded risk thresholds.

**Final Goal:** A fully production-ready system with a zero-trust security model, full observability, human-in-the-loop feedback loops, and enterprise system sync (CRM/ERP), capable of processing high volumes of contracts safely and efficiently.

## Architecture & Tech Stack
- **Ingestion & Parsing:** Python-based (`pypdf`, `python-docx`), rule-based regex segmentation.
- **Orchestration:** Lyzr (currently executing in-process, synchronously).
- **Retrieval (RAG):** Qdrant (currently mocked with in-memory fallback, ready for `qdrant-client` & `fastembed`).
- **AI Agents:** Google ADK (currently mocked heuristic keyword analysis, but uses real CRISPE prompts for easy LLM swap).
  - *Legal Intelligence Agent:* Analyzes risks.
  - *Redline & Summary Agent:* Synthesizes protective contract edits.
- **Rules Engine:** Python declarative rules (`DeterministicPolicyValidator`).
- **API Layer:** FastAPI with `uvicorn` and Pydantic models for the HTTP boundary.
- **Data Models:** Currently `dataclasses` (no network install at project start), migrating to `pydantic` in the future (FR-105).

## Current Status (End of Slice 3)
1. **Slice 1 (Core Pipeline):** Completed. Ingestion, Orchestrator, Mock Agents, Mock Qdrant retrieval, and base pipeline logic are working end-to-end via CLI.
2. **Slice 2 (Deterministic Policy Validator):** Completed. Enforces business rules (FR-106). Escalate risks based on corporate policy matches (from RAG) and mandates human review for low confidence (< 0.8) or high/critical risk. 
3. **Slice 3 (FastAPI Wrapper):** Completed. Exposes the synchronous pipeline over HTTP via `POST /api/v1/contracts/analyze`. Uses Pydantic for response models.

**Tests:** 36/36 tests are passing.

## Next Steps / Future Sprints
- **Slice 4 (Human Review Workspace UI):** Build a frontend application to consume the API, display the `policy_decisions` and `redlines`, and capture user feedback.
- **Pydantic Migration (FR-105):** Refactor `src/models/schemas.py` to use Pydantic native validators instead of `dataclasses`. (Highly recommended to ensure LLM payload strictness).
- **Un-mocking (Production Connections):**
  - Implement real Google ADK LLM network calls in the agents.
  - Implement real Qdrant connection for hybrid search.
  - Replace dummy `scan_for_malware` with ClamAV.
- **Asynchronous Execution:** Convert FastAPI endpoints to `async def` and implement asynchronous Lyzr execution to handle I/O bound LLM calls and queueing (RabbitMQ/Kafka).

## Deployment & Production Strategy (Target state)
- **Containerization & Orchestration:** Dockerized microservices deployed on Kubernetes (K8s) with Horizontal Pod Autoscaling.
- **Security Perimeter (Zero-Trust):** Enterprise API Gateway handles OAuth 2.0 / OIDC authentication with JWT validation. TLS 1.3 across all services. HashiCorp Vault for secrets management.
- **Data Encryption:** AES-256 for data at rest (S3, Qdrant, PostgreSQL).
- **Observability:** OpenTelemetry for tracing (Correlation IDs), Arize Phoenix for AI metrics (hallucination rates, token usage), Prometheus/Grafana for infrastructure.
- **Resilience:** Circuit Breakers & Exponential Backoff for LLM provider calls (via `tenacity`).
- **Disaster Recovery:** Active-Passive PostgreSQL, Multi-node Qdrant clustering. RPO: 1 hour, RTO: 4 hours.

## Agent Directives (Behavioral Rules)
1. **Scope Boundaries:** Always confirm which "Slice" or specific component you are working on. Do not start work on future slices unless explicitly instructed.
2. **Mock Preservation:** When editing the mocked agents (`src/agents/*.py`) or Qdrant (`src/retrieval/qdrant_mock.py`), do NOT accidentally convert them to real network calls unless instructed.
3. **Testing:** Never weaken or delete existing tests. Run `python -m unittest discover -s tests -v` after every change to ensure all 36+ tests pass.
4. **Pydantic/Dataclasses constraint:** Only the API boundary (`src/api/models.py`) uses Pydantic currently. The internal pipeline uses Python `dataclasses` with `.validate()` methods. Do not convert the core models without explicit clearance (FR-105 migration).
