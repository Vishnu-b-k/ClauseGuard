"""
Google ADK Legal Intelligence Agent (FR-104) -- primary analysis agent.

build_prompt() is real: it's the exact CRISPE-formatted prompt (per the
PRD's Prompt Engineering Standards) that would be sent to GPT-4o via
Google ADK. It's usable today for prompt review/eval even without API
access.

analyze() is MOCKED: instead of calling the LLM, it runs a small
keyword-heuristic risk scorer so the pipeline produces plausible,
evidence-grounded findings end-to-end right now.

TODO: swap the body of analyze() for a real ADK agent invocation using
build_prompt(), parse the LLM's JSON response into AgentFinding, and run
it through the Structured Output Validation Layer's repair path (see
src/orchestrator/lyzr_orchestrator.py) on parse failure. Keep the
(clause, evidence) -> AgentFinding contract identical.
"""

from __future__ import annotations

import re

from src.agents.base import ADKAgent
from src.models.schemas import AgentFinding, Clause, RetrievedEvidence, RiskLevel

# Keyword -> (risk_level, human-readable rationale fragment)
# Deliberately simple and inspectable -- a real LLM call replaces this
# entirely; this exists so the mock produces defensible-looking output.
_RISK_SIGNALS: list[tuple[re.Pattern, RiskLevel, str]] = [
    (re.compile(r"unlimited liability|uncapped liability|without limitation", re.I),
     RiskLevel.CRITICAL, "unlimited/uncapped liability exposure"),
    (re.compile(r"indemnify.*any and all|regardless of cause|hold harmless.*all claims", re.I),
     RiskLevel.HIGH, "unusually broad indemnification obligation"),
    (re.compile(r"sole discretion|for any reason|without cause", re.I),
     RiskLevel.MEDIUM, "unilateral right with no stated justification"),
    (re.compile(r"perpetu\w*|evergreen|automatically renew", re.I),
     RiskLevel.MEDIUM, "auto-renewal / perpetual term language"),
    (re.compile(r"no notice|without notice", re.I),
     RiskLevel.MEDIUM, "action permitted without advance notice"),
    (re.compile(r"irrevocable", re.I),
     RiskLevel.MEDIUM, "irrevocable commitment with no exit path"),
]

_CRISPE_TEMPLATE = """\
### CONTEXT
You are analyzing one clause extracted from an enterprise contract as part
of an automated legal compliance review. The clause has been paired with
retrieved evidence (standard clauses and internal policy) from the
organization's legal knowledge base.

### ROLE
You are a senior contracts counsel with expertise in commercial risk
assessment. You are conservative: when uncertain, you flag rather than
clear.

### INSTRUCTIONS
Given the CLAUSE and the RETRIEVED EVIDENCE below:
1. Classify the clause's risk_level as one of: low, medium, high, critical.
2. Assign a confidence score from 0.0 to 1.0 reflecting how certain you are
   in that classification given the evidence available.
3. Cite the evidence_id(s) that most directly informed your classification.
   Do not classify ungrounded -- if no evidence supports a judgment, say so
   and lower your confidence accordingly.
4. Reference any policy_id(s) from the evidence that the clause may violate.
5. Provide a one-to-two sentence rationale a compliance officer could read
   without additional context.

### STEPS
Step 1 -- Compare the clause's language against each evidence item.
Step 2 -- Identify whether the clause matches a "standard_clause" pattern
(baseline risk) or diverges toward a flagged "policy" pattern (elevated risk).
Step 3 -- Assign risk_level and confidence based on the strength of that
match, not on the clause's subject matter alone.
Step 4 -- Write the rationale.

### PERSONALITY
Precise, evidence-first, no hedging language ("might", "could possibly") --
state the classification and the confidence score plainly.

### EXPECTED OUTPUT
Return ONLY valid JSON matching this shape:
{{
  "risk_level": "low" | "medium" | "high" | "critical",
  "confidence": <float 0.0-1.0>,
  "cited_evidence_ids": ["<evidence_id>", ...],
  "policy_refs": ["<policy_id>", ...],
  "rationale": "<string>"
}}

### CLAUSE
clause_id: {clause_id}
text: \"\"\"{clause_text}\"\"\"

### RETRIEVED EVIDENCE
{evidence_block}
"""


class LegalIntelligenceAgent(ADKAgent):
    def build_prompt(self, clause: Clause, evidence: list[RetrievedEvidence]) -> str:
        evidence_block = "\n".join(
            f"- [{ev.evidence_id}] ({ev.source.value}, score={ev.similarity_score}) {ev.text}"
            for ev in evidence
        ) or "(no evidence retrieved)"

        return _CRISPE_TEMPLATE.format(
            clause_id=clause.clause_id,
            clause_text=clause.text,
            evidence_block=evidence_block,
        )

    def analyze(self, clause: Clause, evidence: list[RetrievedEvidence]) -> AgentFinding:
        """MOCK. Replace with a real ADK call; see module docstring."""
        normalized_text = re.sub(r"\s+", " ", clause.text)
        matched_signals = [
            (level, why) for pattern, level, why in _RISK_SIGNALS
            if pattern.search(normalized_text)
        ]

        if matched_signals:
            risk_level = max((lvl for lvl, _ in matched_signals), key=RiskLevel.ordinal)
            reasons = "; ".join(why for _, why in matched_signals)
        else:
            risk_level = RiskLevel.LOW
            reasons = "no elevated-risk language patterns detected"

        # Confidence: starts high when the classification is clear-cut
        # (either a keyword signal fired, or none did and we're calling
        # it low-risk) and gets a small further bump from evidence
        # strength. Drops sharply when evidence is thin or absent, since
        # an ungrounded finding shouldn't be trusted regardless of how
        # clean the keyword match looked -- that's what makes the 0.8
        # threshold in FR-106 actually selective instead of firing on
        # every clause.
        avg_evidence_score = (
            sum(e.similarity_score for e in evidence) / len(evidence) if evidence else 0.0
        )
        base_confidence = 0.85 if (matched_signals or risk_level == RiskLevel.LOW) else 0.65
        evidence_bonus = min(avg_evidence_score * 0.3, 0.13)
        confidence = round(min(base_confidence + evidence_bonus, 0.98), 2)

        if not evidence:
            confidence = min(confidence, 0.55)  # can't ground it, don't trust it
        elif avg_evidence_score < 0.05:
            confidence = min(confidence, 0.65)  # evidence retrieved but barely relevant

        cited_ids = [e.evidence_id for e in evidence[:3]] or ["NONE-RETRIEVED"]
        policy_refs = [
            e.metadata.get("policy_id") for e in evidence
            if e.metadata.get("policy_id")
        ]

        finding = AgentFinding(
            clause_id=clause.clause_id,
            risk_level=risk_level,
            confidence=confidence,
            rationale=(
                f"Clause flagged {risk_level.value} risk: {reasons}. "
                f"Grounded against {len(evidence)} retrieved evidence item(s)."
            ),
            cited_evidence_ids=cited_ids,
            policy_refs=policy_refs,
        )
        finding.validate()
        return finding
