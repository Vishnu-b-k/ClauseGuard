"""
Document Intelligence Pipeline: clause segmentation (FR-102).

Real, rule-based segmentation -- no LLM call needed for this step, so
nothing here is mocked. Splits on common legal numbering conventions
(1., 1.1, Section 2, Article III) and falls back to paragraph breaks
for contracts that don't number clauses.

A production upgrade path (per the architecture's Document Intelligence
node) would add layout-aware parsing for scanned/complex PDFs -- this
covers clean-text and simple-PDF contracts, which is the right scope
for this sprint slice.
"""

from __future__ import annotations

import re
from typing import List

from src.models.schemas import Clause

# Matches "1.", "1.1", "1.1.2", "Section 3", "Article IV", "(a)" at line start
_CLAUSE_HEADER_RE = re.compile(
    r"^\s*(?:"
    r"\d+(?:\.\d+)*\.?\s+"
    r"|Section\s+\d+\b"
    r"|Article\s+[IVXLC]+\b"
    r"|\([a-z]\)\s+"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

# Rough keyword->type map so downstream agents get a small head start.
# This is a hint, not ground truth -- the Legal Intelligence Agent does
# the real classification.
_TYPE_HINTS = {
    "liability": ["liability", "liable", "damages"],
    "termination": ["terminat", "cancel"],
    "indemnification": ["indemnif", "hold harmless"],
    "confidentiality": ["confidential", "non-disclosure", "nda"],
    "renewal": ["renew", "auto-renew", "evergreen"],
    "governing_law": ["governing law", "jurisdiction", "venue"],
    "ip_assignment": ["intellectual property", "assign", "work product"],
    "payment": ["payment", "invoice", "fee", "compensation"],
}


def _guess_clause_type(text: str) -> str | None:
    normalized_text = re.sub(r"\s+", " ", text.lower())
    for clause_type, keywords in _TYPE_HINTS.items():
        if any(kw in normalized_text for kw in keywords):
            return clause_type
    return None


def segment_into_clauses(text: str, contract_id: str) -> List[Clause]:
    """Splits raw contract text into Clause objects.

    Strategy: find numbered/section headers as split points; if fewer
    than 2 are found (unnumbered contract), fall back to splitting on
    blank lines (paragraph breaks).
    """
    text = text.strip()
    if not text:
        return []

    header_matches = list(_CLAUSE_HEADER_RE.finditer(text))

    if len(header_matches) >= 2:
        boundaries = [m.start() for m in header_matches] + [len(text)]
        spans = list(zip(boundaries[:-1], boundaries[1:]))
    else:
        # Fallback: paragraph-based split
        spans = []
        cursor = 0
        for para in re.split(r"\n\s*\n", text):
            if not para.strip():
                cursor += len(para) + 2
                continue
            start = text.find(para, cursor)
            end = start + len(para)
            spans.append((start, end))
            cursor = end

    clauses: List[Clause] = []
    for start, end in spans:
        chunk = text[start:end].strip()
        if not chunk:
            continue
        clause = Clause(
            contract_id=contract_id,
            text=chunk,
            clause_type_guess=_guess_clause_type(chunk),
            start_offset=start,
            end_offset=end,
        )
        clause.validate()
        clauses.append(clause)

    return clauses
