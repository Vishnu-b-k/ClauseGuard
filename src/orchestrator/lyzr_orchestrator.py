"""
Lyzr Legal Workflow Orchestrator (System Components: "Coordinates
multi-agent task planning and state management").

Runs synchronously, in-process, clause by clause. That's the right scope
for this sprint slice -- the architecture's Message Queue / async
processing (FR-108 territory, "Enterprise System Sync") is a later
increment, not needed to prove the core pipeline out.

Also plays the role of the Structured Output Validation Layer (FR-105):
wraps each agent call, and on a validation failure attempts one repair
retry before escalating to human review rather than dropping the clause
silently.

Delegates all policy logic to the Deterministic Policy Validator (FR-106):
confidence-threshold routing, risk-level gates, and policy-ref escalation
are now handled by src/rules/deterministic_policy_validator.py, not inline
in this orchestrator.
"""

import asyncio
import time

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

from src.agents.legal_intelligence_agent import LegalIntelligenceAgent
from src.agents.redline_summary_agent import RedlineSummaryAgent
from src.config import RETRIEVAL_TOP_K
from src.ingestion.clause_segmenter import segment_into_clauses
from src.models.schemas import (
    AgentFinding,
    PipelineResult,
    RiskLevel,
    SchemaValidationError,
)
from src.retrieval.base import RetrievalClient
from src.rules.deterministic_policy_validator import DeterministicPolicyValidator

_REDLINE_TRIGGER_LEVELS = {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}


class LyzrWorkflowOrchestrator:
    def __init__(
        self,
        retrieval_client: RetrievalClient,
        intelligence_agent: LegalIntelligenceAgent | None = None,
        redline_agent: RedlineSummaryAgent | None = None,
        policy_validator: DeterministicPolicyValidator | None = None,
        retrieval_top_k: int = RETRIEVAL_TOP_K,
    ):
        self.retrieval_client = retrieval_client
        self.intelligence_agent = intelligence_agent or LegalIntelligenceAgent()
        self.redline_agent = redline_agent or RedlineSummaryAgent()
        self.policy_validator = policy_validator or DeterministicPolicyValidator()
        self.retrieval_top_k = retrieval_top_k

    def _analyze_with_validation(self, clause, evidence, warnings: list[str]) -> AgentFinding | None:
        """Structured Output Validation Layer (FR-105): one repair retry,
        then escalate rather than fail silently."""
        for attempt in (1, 2):
            try:
                finding = self.intelligence_agent.analyze(clause, evidence)
                finding.validate()
                return finding
            except SchemaValidationError as exc:
                warnings.append(
                    f"{clause.clause_id}: validation failed on attempt {attempt} ({exc})"
                )
        warnings.append(
            f"{clause.clause_id}: escalated to human review after repeated validation failure"
        )
        return None

    async def run(self, contract_text: str, contract_id: str) -> PipelineResult:
        with tracer.start_as_current_span("orchestrator.run") as span:
            span.set_attribute("contract_id", contract_id)
            start = time.perf_counter()
            warnings: list[str] = []

            clauses = segment_into_clauses(contract_text, contract_id)
            span.set_attribute("clauses.count", len(clauses))

            findings: list[AgentFinding] = []
            policy_decisions = []
            redlines = []
            flagged_for_review: list[str] = []

            queue = asyncio.Queue()
            for clause in clauses:
                await queue.put(clause)

            async def worker():
                while True:
                    try:
                        clause = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                    
                    with tracer.start_as_current_span("orchestrator.process_clause") as clause_span:
                        clause_span.set_attribute("clause_id", clause.clause_id)
                        def _do_work():
                            evidence = self.retrieval_client.retrieve(clause.text, top_k=self.retrieval_top_k)
                            clause_span.set_attribute("evidence.count", len(evidence))
                            finding = self._analyze_with_validation(clause, evidence, warnings)
                            if finding is None:
                                return None, None, None
                            
                            decision = self.policy_validator.validate(finding)
                            clause_span.set_attribute("risk_level", finding.risk_level.value)
                            clause_span.set_attribute("final_risk_level", decision.final_risk_level.value)
                            
                            redline = None
                            if decision.final_risk_level in _REDLINE_TRIGGER_LEVELS:
                                redline = self.redline_agent.generate(clause, finding)
                                clause_span.set_attribute("redline.generated", True)
                            return finding, decision, redline

                        finding, decision, redline = await asyncio.to_thread(_do_work)

                        if finding is None:
                            flagged_for_review.append(clause.clause_id)
                        else:
                            findings.append(finding)
                            policy_decisions.append(decision)
                            if decision.requires_human_review:
                                flagged_for_review.append(clause.clause_id)
                            if redline:
                                redlines.append(redline)
                    
                    queue.task_done()

            # Use 5 concurrent workers for I/O bound LLM calls
            workers = [asyncio.create_task(worker()) for _ in range(5)]
            await asyncio.gather(*workers)

            elapsed_ms = (time.perf_counter() - start) * 1000
            span.set_attribute("processing_time_ms", elapsed_ms)

        result = PipelineResult(
            contract_id=contract_id,
            clauses_processed=len(clauses),
            findings=findings,
            redlines=redlines,
            flagged_for_review=flagged_for_review,
            policy_decisions=policy_decisions,
            warnings=warnings,
            processing_time_ms=elapsed_ms,
        )
        result.validate()
        return result
