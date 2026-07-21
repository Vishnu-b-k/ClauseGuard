"""
Google ADK Redline & Summary Agent (FR-104) -- synthesis agent.

Same pattern as the Legal Intelligence Agent: build_prompt() is real and
CRISPE-formatted; generate() is MOCKED with simple template substitution
so flagged clauses get a plausible, structured redline end-to-end today.

TODO: swap generate()'s body for a real ADK call using build_prompt();
parse the LLM's JSON into RedlineSuggestion.
"""

from __future__ import annotations

import re

from src.agents.base import ADKAgent
from src.models.schemas import AgentFinding, Clause, RedlineSuggestion

_CRISPE_TEMPLATE = """\
### CONTEXT
A clause from an enterprise contract has been flagged during automated
compliance review. Your job is to draft an alternative version that
resolves the flagged risk while preserving the clause's commercial intent.

### ROLE
You are a senior contracts counsel drafting a redline for the business
team to send back to the counterparty.

### INSTRUCTIONS
Given the CLAUSE and the FINDING below:
1. Rewrite the clause to address the specific risk in the finding's
   rationale -- do not rewrite unrelated parts of the clause.
2. Keep the redline as close to the original structure/length as
   reasonable; enterprise counterparties respond better to minimal,
   targeted edits than full rewrites.
3. Write a one-sentence rationale explaining what changed and why.
4. Write a one-sentence executive summary suitable for a non-lawyer
   stakeholder skimming a review queue.

### STEPS
Step 1 -- Identify the specific risky language named in the finding.
Step 2 -- Propose the smallest edit that neutralizes it (e.g., add a cap,
add a notice period, narrow a scope).
Step 3 -- Write the rationale and executive summary.

### PERSONALITY
Business-pragmatic. Prefer edits a counterparty is likely to accept over
maximally protective language that kills the deal.

### EXPECTED OUTPUT
Return ONLY valid JSON matching this shape:
{{
  "suggested_text": "<string>",
  "rationale": "<string>",
  "executive_summary": "<string>"
}}

### CLAUSE
clause_id: {clause_id}
original_text: \"\"\"{clause_text}\"\"\"

### FINDING
risk_level: {risk_level}
rationale: {finding_rationale}
"""

# (pattern, redline transform, short label) -- mocked "what a targeted
# edit looks like" for the most common flagged patterns. A real LLM call
# replaces this entirely.
_REDLINE_RULES: list[tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"unlimited liability|uncapped liability|without limitation", re.I),
        "cap liability",
        "capped liability at 12 months' fees paid under this Agreement",
    ),
    (
        re.compile(r"indemnify.*any and all|regardless of cause", re.I),
        "narrow indemnification",
        "limited indemnification to direct damages arising from gross negligence "
        "or willful misconduct, excluding indirect or consequential damages",
    ),
    (
        re.compile(r"sole discretion|for any reason|without cause", re.I),
        "add justification requirement",
        "required the right to be exercised only for a documented material breach",
    ),
    (
        re.compile(r"perpetu\w*|evergreen|automatically renew", re.I),
        "add notice window",
        "added a 30-day advance written notice requirement before auto-renewal takes effect",
    ),
    (
        re.compile(r"no notice|without notice", re.I),
        "add notice period",
        "added a minimum 30-day advance notice requirement",
    ),
]


class RedlineSummaryAgent(ADKAgent):
    def build_prompt(self, clause: Clause, finding: AgentFinding) -> str:
        return _CRISPE_TEMPLATE.format(
            clause_id=clause.clause_id,
            clause_text=clause.text,
            risk_level=finding.risk_level.value,
            finding_rationale=finding.rationale,
        )

    def generate(self, clause: Clause, finding: AgentFinding) -> RedlineSuggestion:
        """MOCK. Replace with a real ADK call; see module docstring."""
        applied_edits: list[str] = []
        suggested = clause.text
        normalized_text = re.sub(r"\s+", " ", clause.text)

        for pattern, label, edit_description in _REDLINE_RULES:
            if pattern.search(normalized_text):
                applied_edits.append(edit_description)

        if applied_edits:
            suggested = (
                f"{clause.text.rstrip('.')}, provided that this clause is hereby "
                f"amended so that it is {'; and '.join(applied_edits)}."
            )
            rationale = (
                f"Addressed {finding.risk_level.value}-risk language by applying: "
                f"{'; '.join(applied_edits)}."
            )
        else:
            suggested = (
                f"{clause.text.rstrip('.')}, subject to review by Legal for "
                f"alignment with standard risk tolerances."
            )
            rationale = (
                f"No specific pattern-based edit matched; flagged for manual "
                f"drafting given {finding.risk_level.value} risk classification."
            )

        redline = RedlineSuggestion(
            clause_id=clause.clause_id,
            original_text=clause.text,
            suggested_text=suggested,
            rationale=rationale,
            executive_summary=(
                f"Clause {clause.clause_id}: {finding.risk_level.value} risk, "
                f"redline proposed to reduce exposure."
            ),
        )
        redline.validate()
        return redline
