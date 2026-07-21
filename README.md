# Legal AI Contract Compliance — Core Pipeline (Build Sprint slice 1)

This is the first three build-sprint slices of the platform described in the PRD:
**ingestion → Lyzr orchestrator → Qdrant retrieval → 2 Google ADK agents**,
plus the **Deterministic Policy Validator**, all wrapped in a **FastAPI** service.
The human review workspace is deliberately left for the next slice.

## What's real vs. mocked

No API keys exist yet, so nothing that requires Google ADK, Qdrant, or
Lyzr credentials is faked at the *interface* level, only at the
*implementation* level — every mock sits behind an abstract interface so
swapping in the real thing later touches exactly one file.

| Component | Status | File |
|---|---|---|
| PDF/DOCX/TXT text extraction | **Real** | `src/ingestion/document_parser.py` |
| Clause segmentation | **Real** (regex-based) | `src/ingestion/clause_segmenter.py` |
| Malware scanning | Mocked (always clean) | `document_parser.py::scan_for_malware` |
| Qdrant hybrid retrieval | Mocked (in-memory corpus, real hybrid scoring logic) | `src/retrieval/qdrant_mock.py` |
| Legal Intelligence Agent | Mocked call, **real** CRISPE prompt | `src/agents/legal_intelligence_agent.py` |
| Redline & Summary Agent | Mocked call, **real** CRISPE prompt | `src/agents/redline_summary_agent.py` |
| Deterministic Policy Validator | **Real** (declarative rules engine) | `src/rules/deterministic_policy_validator.py` |
| Lyzr orchestration logic | **Real** (runs in-process, sequentially) | `src/orchestrator/lyzr_orchestrator.py` |
| Structured Output Validation | **Real** (validate + one repair retry + escalate) | same file |
| API Wrapper | **Real** (FastAPI) | `src/api/app.py` |

"Mocked call, real prompt" means: `build_prompt()` on each agent returns
the exact CRISPE-formatted prompt that would be sent to GPT-4o via ADK
today — read it, eval it, tune it now. Only the network call is stubbed.

## Why dataclasses instead of Pydantic

FR-105 specifies Pydantic for schema validation. `src/models/schemas.py`
uses stdlib `dataclasses` instead, purely because this sandbox has no
network access to `pip install pydantic`. Every field name and type
mirrors what the Pydantic models would look like, and each dataclass has
its own `validate()` method doing the same job a Pydantic validator
would. See the docstring at the top of `schemas.py` for the exact swap.

## Running it

### CLI
```bash
pip install -r requirements.txt
python3 -m src.main sample_data/sample_contract.txt
python3 -m unittest discover -s tests -v
```

### API
```bash
uvicorn src.api.app:app --reload
```
Once running, you can access the interactive OpenAPI docs at `http://localhost:8000/docs`.

### Frontend UI (Slice 4)
Requires the API to be running on port 8000.
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to access the Human Review Workspace.

The sample contract has one deliberately critical clause (uncapped
liability), one medium clause (unilateral termination with no notice),
and several clean clauses — enough variation to see confidence-based
routing actually discriminate rather than flagging everything.

## PRD requirement traceability (this slice)

| ID | Requirement | Where |
|---|---|---|
| FR-101 | Secure Contract Ingestion | `src/ingestion/document_parser.py` |
| FR-102 | Clause Segmentation | `src/ingestion/clause_segmenter.py` |
| FR-103 | Hybrid Retrieval (RAG) | `src/retrieval/qdrant_mock.py` + `base.py` |
| FR-104 | Multi-Agent Reasoning | `src/agents/*.py` |
| FR-105 | Structured Output Validation | `src/models/schemas.py` (`validate()`) + orchestrator's repair/escalate path |
| FR-106 | Deterministic Policy Validation | `src/rules/deterministic_policy_validator.py` |
| FR-107 | Human-in-the-Loop Feedback | **Not in this slice** — `flagged_for_review` list is produced, no review UI or feedback capture yet |

## Known limitations of this slice (by design, not oversight)

- **Orchestration is synchronous and in-process.** No Message Queue, no
  Lyzr workflow-state persistence — fine for one contract at a time in a
  demo, not for the throughput NFRs (NFR-202) in the PRD.
- **Risk/confidence scoring is keyword-heuristic, not an LLM call.** It's
  deliberately inspectable (see `_RISK_SIGNALS` in
  `legal_intelligence_agent.py`) so you can verify the pipeline's
  *plumbing* is correct before spending API budget on real LLM calls.
- **The mock Qdrant corpus is 10 hand-written entries.** It's there to
  exercise the hybrid-retrieval code path, not to be representative
  legal content.
- **No Deterministic Policy Validator yet.** This slice only has the two
  ADK agents; the rules engine that combines their output with hardcoded
  policy (per FR-106 and the architecture's "Deterministic Policy
  Validator" node) is the natural next build-sprint slice.

## Swapping in real services later

1. **Qdrant:** implement `RetrievalClient` in a new file using
   `qdrant_client.QdrantClient` + `fastembed`; point `src/main.py` at it
   instead of `MockQdrantRetrievalClient`.
2. **Google ADK:** replace the body of `analyze()` / `generate()` in each
   agent file with a real ADK call using the existing `build_prompt()`
   output; keep the return type (`AgentFinding` / `RedlineSuggestion`)
   identical.
3. **Lyzr:** replace the sequential loop in
   `LyzrWorkflowOrchestrator.run()` with real Lyzr task orchestration
   once you're moving past single-contract synchronous demos.
4. **Pydantic:** once `pip install pydantic` works in your environment,
   follow the swap note at the top of `src/models/schemas.py`.
