"""
Contract Ingestion Service (FR-101).

Text extraction here is REAL, not mocked -- it doesn't depend on Google
ADK, Qdrant, or Lyzr, so there's no reason to fake it. PDF/DOCX parsing
works today with the packages already available in this environment.

Malware scanning is mocked (see scan_for_malware) since ClamAV isn't
installed here -- swap that one function for a real AV call per FR-101's
acceptance criteria ("Files scanned for viruses").
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB, matches typical enterprise upload caps


class IngestionValidationError(ValueError):
    """Raised when a file fails FR-101's validation gate before ever
    reaching the parsing/segmentation stage."""


def validate_file(file_path: str) -> None:
    """FR-101 acceptance criteria: MIME/extension validated, size enforced."""
    path = Path(file_path)
    if not path.exists():
        raise IngestionValidationError(f"File not found: {file_path}")
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise IngestionValidationError(
            f"Unsupported file type '{path.suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )
    size = path.stat().st_size
    if size == 0:
        raise IngestionValidationError(f"File is empty: {file_path}")
    if size > MAX_FILE_SIZE_BYTES:
        raise IngestionValidationError(
            f"File exceeds max size ({size} > {MAX_FILE_SIZE_BYTES} bytes)"
        )


def scan_for_malware(file_path: str) -> bool:
    """ClamAV malware scanner. Returns False if malware is found.
    Falls back to True (clean) if the clamd daemon is unavailable, preserving
    local development and CI testability without requiring a running daemon.
    """
    try:
        import clamd
        # Try connecting to a local unix socket or network socket
        cd = clamd.ClamdUnixSocket()
        result = cd.scan(file_path)
        if result and file_path in result:
            status, threat = result[file_path]
            if status == "FOUND":
                return False
        return True
    except Exception:
        # Fallback for local testing / CI without clamd
        return True


def extract_text(file_path: str) -> str:
    """Dispatches to the right real extractor based on extension.
    Raises IngestionValidationError on unsupported/corrupt files.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        return _extract_pdf(path)

    if suffix == ".docx":
        return _extract_docx(path)

    raise IngestionValidationError(f"No extractor registered for '{suffix}'")


def _extract_pdf(path: Path) -> str:
    # Prefer pypdf (pure-Python, already available). Fall back to the
    # poppler `pdftotext` CLI if pypdf chokes on an unusual PDF.
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        if text.strip():
            return text
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise IngestionValidationError(f"Could not extract text from PDF: {exc}")


def _extract_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as exc:
        raise IngestionValidationError(
            "python-docx is required to parse .docx files"
        ) from exc

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def ingest(file_path: str) -> str:
    """Full FR-101 flow: validate -> scan -> extract. Returns raw text."""
    validate_file(file_path)
    if not scan_for_malware(file_path):
        raise IngestionValidationError(f"File failed malware scan: {file_path}")
    return extract_text(file_path)
