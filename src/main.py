"""
CLI entrypoint: runs the core pipeline (FR-101 -> FR-105) end to end
against one contract file.

Usage:
    python3 -m src.main sample_data/sample_contract.txt
    python3 -m src.main path/to/contract.pdf --out output/result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:
    pass

from src.config import MOCK_MODE
from src.ingestion.document_parser import ingest, IngestionValidationError
from src.orchestrator.lyzr_orchestrator import LyzrWorkflowOrchestrator
from src.retrieval import get_retrieval_client


def _print_summary(result, retrieval_client=None) -> None:
    risk_counts: dict[str, int] = {}
    for f in result.findings:
        risk_counts[f.risk_level.value] = risk_counts.get(f.risk_level.value, 0) + 1

    client_name = retrieval_client.__class__.__name__ if retrieval_client else "Unknown"
    print(f"\nContract: {result.contract_id}")
    print(f"Retrieval Engine: {client_name} (MOCK_MODE={MOCK_MODE})")
    print(f"Clauses processed: {result.clauses_processed}")
    print(f"Processing time: {result.processing_time_ms:.1f} ms")
    print(f"\nRisk breakdown (AI agent):")
    for level in ("critical", "high", "medium", "low"):
        if level in risk_counts:
            print(f"  {level:>8}: {risk_counts[level]}")
    final_risk_counts: dict[str, int] = {}
    for d in result.policy_decisions:
        final_risk_counts[d.final_risk_level.value] = (
            final_risk_counts.get(d.final_risk_level.value, 0) + 1
        )
    if final_risk_counts != risk_counts:
        print(f"\nRisk breakdown (after policy validation):")
        for level in ("critical", "high", "medium", "low"):
            if level in final_risk_counts:
                print(f"  {level:>8}: {final_risk_counts[level]}")
    print(f"\nFlagged for human review: {len(result.flagged_for_review)} clause(s)")
    for cid in result.flagged_for_review:
        finding = next((f for f in result.findings if f.clause_id == cid), None)
        decision = next((d for d in result.policy_decisions if d.clause_id == cid), None)
        if finding and decision:
            rules = ", ".join(r.rule_id for r in decision.rules_fired)
            cited = ", ".join(finding.cited_evidence_ids) if finding.cited_evidence_ids else "none"
            print(
                f"  - {cid} [{finding.risk_level.value}->{decision.final_risk_level.value}, "
                f"conf={finding.confidence}] rules: {rules}"
            )
            print(f"    Rationale: {finding.rationale}")
            print(f"    Cited Evidence: [{cited}]")
        elif finding:
            cited = ", ".join(finding.cited_evidence_ids) if finding.cited_evidence_ids else "none"
            print(f"  - {cid} [{finding.risk_level.value}, conf={finding.confidence}] {finding.rationale}")
            print(f"    Cited Evidence: [{cited}]")
        else:
            print(f"  - {cid} [validation escalation]")
    print(f"\nRedlines proposed: {len(result.redlines)}")
    for r in result.redlines:
        print(f"  - {r.clause_id}: {r.executive_summary}")
    if result.warnings:
        print(f"\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Legal AI core pipeline on one contract.")
    parser.add_argument("contract_path", help="Path to a .txt, .pdf, or .docx contract")
    parser.add_argument("--out", default="output/pipeline_result.json", help="Where to write the full JSON result")
    args = parser.parse_args()

    try:
        text = ingest(args.contract_path)
    except IngestionValidationError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    contract_id = Path(args.contract_path).stem
    retrieval_client = get_retrieval_client()
    orchestrator = LyzrWorkflowOrchestrator(retrieval_client=retrieval_client)
    result = orchestrator.run(text, contract_id=contract_id)

    _print_summary(result, retrieval_client=retrieval_client)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.to_dict(), indent=2))
    print(f"\nFull result written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
