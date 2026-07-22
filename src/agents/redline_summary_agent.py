"""
Google ADK Redline & Summary Agent (FR-104) -- synthesis agent.

build_prompt() is real and CRISPE-formatted.
generate() invokes real Google ADK (`google.genai` / Gemini) when MOCK_MODE=False
and GOOGLE_API_KEY is present, with tenacity retries and JSON repair forwarding.
When MOCK_MODE=True or offline, runs heuristic template redlines.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.agents.base import ADKAgent
from src.config import (
    GOOGLE_API_KEY,
    LLM_MAX_RETRIES,
    LLM_MODEL,
    LLM_TIMEOUT_SEC,
    MOCK_MODE,
)
from src.models.schemas import (
    AgentFinding,
    Clause,
    RedlineSuggestion,
    SchemaValidationError,
)

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
# edit looks like" for the most common flagged patterns when MOCK_MODE is True.
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

    @retry(
        stop=stop_after_attempt(LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _invoke_llm(self, prompt: str) -> str:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    def _run_mock_generate(self, clause: Clause, finding: AgentFinding) -> RedlineSuggestion:
        """Heuristic mock redline synthesis when MOCK_MODE is True or no API key."""
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

    def generate(self, clause: Clause, finding: AgentFinding) -> RedlineSuggestion:
        if MOCK_MODE or not GOOGLE_API_KEY:
            return self._run_mock_generate(clause, finding)

        prompt = self.build_prompt(clause, finding)
        raw_json = self._invoke_llm(prompt)

        cleaned = raw_json.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                raise ValueError("JSON output must be a dictionary")

            suggested_text = str(data.get("suggested_text", "")).strip()
            if not suggested_text:
                suggested_text = f"{clause.text} [AMENDED FOR COMPLIANCE]"

            rationale = str(data.get("rationale", "")).strip()
            if not rationale:
                rationale = f"Proposed redline to address {finding.risk_level.value} risk."

            exec_summary = str(data.get("executive_summary", "")).strip()
            if not exec_summary:
                exec_summary = f"Clause {clause.clause_id} redlined for {finding.risk_level.value} risk mitigation."

            redline = RedlineSuggestion(
                clause_id=clause.clause_id,
                original_text=clause.text,
                suggested_text=suggested_text,
                rationale=rationale,
                executive_summary=exec_summary,
            )
            redline.validate()
            return redline
        except (json.JSONDecodeError, ValueError, TypeError, SchemaValidationError) as exc:
            raise SchemaValidationError(
                f"Malformed LLM redline output for clause {clause.clause_id}: {exc}"
            ) from exc
