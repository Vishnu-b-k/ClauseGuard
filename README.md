# ClauseGuard: Legal AI Contract Compliance Platform

ClauseGuard is an enterprise-grade solution designed to automate the review, risk assessment, and redlining of legal contracts. Built for high-stakes environments, it combines a cinematic "Dark Luxury" Next.js frontend with a robust, asynchronous Python backend.

## Architecture & Tech Stack

*   **Frontend (Human Review Workspace):** Next.js (App Router), Tailwind CSS, Framer Motion, Lucide Icons. Designed with a dark luxury, cinematic investigation aesthetic.
*   **API Gateway:** FastAPI with Pydantic schemas.
*   **Asynchronous Engine:** Celery workers backed by a **RabbitMQ 3.x** message broker and a local SQLite result backend.
*   **AI Agents (Mocked for Hackathon):** Google ADK architecture ready for drop-in LLM keys. Currently uses deterministic heuristic scoring for reliable demo presentations.
*   **Retrieval (RAG):** Prepared for Qdrant vector database (currently mocked in-memory).

## Running Locally

To run the entire platform locally, you will need four terminal windows.

### 1. Message Broker (Docker Required)
Start a RabbitMQ 3.x instance (do not use 4.x due to transient queue incompatibilities with Celery):
```bash
docker run -d --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

### 2. Celery Worker (AI Execution)
Start the background worker that actually processes the contracts:
```bash
# Ensure your virtual environment is active
celery -A src.worker.celery_app worker --loglevel=info -P solo
```

### 3. FastAPI Server (Backend)
Start the API gateway:
```bash
# Ensure your virtual environment is active
uvicorn src.api.app:app --reload
```
API docs available at `http://localhost:8000/docs`.

### 4. Next.js Frontend (UI)
Start the Dark Luxury investigation console:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to start investigating contracts.

## Swapping in Real Services

1.  **Google ADK:** Replace the body of `analyze()` / `generate()` in `src/agents/` with real LLM calls using the existing `build_prompt()` output.
2.  **Qdrant:** Implement `RetrievalClient` in `src/retrieval/qdrant_client.py` using `fastembed`.
3.  **Database:** Update Phase A configurations in `src/models/db.py` and `celery_app.py` to point to a managed PostgreSQL instance instead of SQLite.
