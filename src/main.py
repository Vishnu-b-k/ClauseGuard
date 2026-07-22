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

from src.bootstrap import create_orchestrator
from src.config import load_settings
from src.ingestion.document_parser import ingest, IngestionValidationError


def _print_summary(result) -> None:
    risk_counts: dict[str, int] = {}
    for finding in result.findings:
        risk_counts[finding.risk_level.value] = risk_counts.get(finding.risk_level.value, 0) + 1

    print(f"\nContract: {result.contract_id}")
    print(f"Clauses processed: {result.clauses_processed}")
    print(f"Processing time: {result.processing_time_ms:.1f} ms")
    print("\nRisk breakdown (AI agent):")
    for level in ("critical", "high", "medium", "low"):
        if level in risk_counts:
            print(f"  {level:>8}: {risk_counts[level]}")

    final_risk_counts: dict[str, int] = {}
    for decision in result.policy_decisions:
        final_risk_counts[decision.final_risk_level.value] = (
            final_risk_counts.get(decision.final_risk_level.value, 0) + 1
        )
    if final_risk_counts != risk_counts:
        print("\nRisk breakdown (after policy validation):")
        for level in ("critical", "high", "medium", "low"):
            if level in final_risk_counts:
                print(f"  {level:>8}: {final_risk_counts[level]}")

    print(f"\nFlagged for human review: {len(result.flagged_for_review)} clause(s)")
    for clause_id in result.flagged_for_review:
        finding = next((item for item in result.findings if item.clause_id == clause_id), None)
        decision = next(
            (item for item in result.policy_decisions if item.clause_id == clause_id),
            None,
        )
        if finding and decision:
            rules = ", ".join(rule.rule_id for rule in decision.rules_fired)
            print(
                f"  - {clause_id} [{finding.risk_level.value}->{decision.final_risk_level.value}, "
                f"conf={finding.confidence}] rules: {rules}"
            )
        elif finding:
            print(
                f"  - {clause_id} [{finding.risk_level.value}, conf={finding.confidence}] "
                f"{finding.rationale}"
            )
        else:
            print(f"  - {clause_id} [validation escalation]")

    print(f"\nRedlines proposed: {len(result.redlines)}")
    for redline in result.redlines:
        print(f"  - {redline.clause_id}: {redline.executive_summary}")
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Legal AI core pipeline on one contract."
    )
    parser.add_argument("contract_path", help="Path to a .txt, .pdf, or .docx contract")
    parser.add_argument(
        "--out",
        default="output/pipeline_result.json",
        help="Where to write the full JSON result",
    )
    args = parser.parse_args()

    try:
        text = ingest(args.contract_path)
    except IngestionValidationError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    try:
        orchestrator = create_orchestrator(load_settings())
    except (RuntimeError, ValueError) as exc:
        print(f"Configuration failed: {exc}", file=sys.stderr)
        return 2

    contract_id = Path(args.contract_path).stem
    result = orchestrator.run(text, contract_id=contract_id)

    _print_summary(result)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.to_dict(), indent=2))
    print(f"\nFull result written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())