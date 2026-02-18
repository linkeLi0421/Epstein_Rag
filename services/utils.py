"""Shared utilities for the data pipeline services."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported document extensions for processing
SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".txt", ".md", ".docx"}

# Extensions that are PDFs (need special extraction)
PDF_EXTENSIONS: set[str] = {".pdf"}


def get_file_extension(path: str | Path) -> str:
    """Return the lowercased file extension including the dot."""
    return Path(path).suffix.lower()


def is_supported_file(path: str | Path) -> bool:
    """Check whether a file has a supported extension for processing."""
    return get_file_extension(path) in SUPPORTED_EXTENSIONS


def is_pdf(path: str | Path) -> bool:
    """Check whether a file is a PDF."""
    return get_file_extension(path) in PDF_EXTENSIONS


def file_hash(path: str | Path, algorithm: str = "sha256") -> str:
    """Compute a hex-digest hash of a file in streaming fashion."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    """Sanitize a string for safe use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    return name or "unnamed"


def extract_date_from_text(text: str) -> str | None:
    """Try to extract the first date-like string from text.

    Looks for common US date formats (MM/DD/YYYY, Month DD YYYY, etc.).
    Returns the matched string or None.
    """
    patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def classify_document_type(filename: str, text_sample: str = "") -> str:
    """Heuristic classification of document type based on filename and content.

    Returns one of: 'flight_log', 'court_document', 'deposition',
    'police_report', 'financial', 'correspondence', 'other'.
    """
    lower_name = filename.lower()
    lower_text = text_sample[:2000].lower()

    classifiers: list[tuple[str, list[str]]] = [
        ("flight_log", ["flight", "manifest", "tail number", "passenger"]),
        ("court_document", ["court", "docket", "ruling", "order", "motion", "plaintiff", "defendant"]),
        ("deposition", ["deposition", "deponent", "sworn", "testimony"]),
        ("police_report", ["police", "arrest", "incident", "officer"]),
        ("financial", ["bank", "transaction", "wire transfer", "account", "invoice"]),
        ("correspondence", ["letter", "memo", "email", "dear", "sincerely"]),
    ]

    combined = lower_name + " " + lower_text
    for doc_type, keywords in classifiers:
        if any(kw in combined for kw in keywords):
            return doc_type
    return "other"


def format_file_size(size_bytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def estimate_eta(processed: int, total: int, elapsed_seconds: float) -> str | None:
    """Estimate remaining time given progress so far."""
    if processed <= 0 or total <= 0:
        return None
    rate = elapsed_seconds / processed
    remaining = (total - processed) * rate
    if remaining < 60:
        return f"{remaining:.0f}s"
    if remaining < 3600:
        return f"{remaining / 60:.0f}m {remaining % 60:.0f}s"
    hours = remaining / 3600
    minutes = (remaining % 3600) / 60
    return f"{hours:.0f}h {minutes:.0f}m"


def ensure_directory(path: str | Path) -> Path:
    """Create a directory (and parents) if it doesn't exist. Return the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_env(key: str, default: str = "") -> str:
    """Read an environment variable with a default."""
    return os.getenv(key, default)
