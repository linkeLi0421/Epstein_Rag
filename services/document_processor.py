"""Document processing pipeline: extraction, chunking, and metadata.

Handles PDF text extraction via PyMuPDF, configurable chunking with overlap,
metadata extraction, and batch/parallel processing with per-document error
handling and resume capability.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generator

from .utils import (
    classify_document_type,
    estimate_eta,
    extract_date_from_text,
    format_file_size,
    get_file_extension,
    is_pdf,
)

logger = logging.getLogger(__name__)

# Progress callback: (processed, total, current_file, status)
ProcessorProgressCallback = Callable[[int, int, str, str], None]


@dataclass
class DocumentChunk:
    """A single chunk of text extracted from a document."""

    text: str
    metadata: dict[str, Any]
    chunk_index: int
    document_id: str


@dataclass
class ProcessedDocument:
    """Result of processing a single document."""

    source_path: str
    filename: str
    chunks: list[DocumentChunk]
    page_count: int
    total_chars: int
    document_type: str
    error: str | None = None


@dataclass
class ProcessingState:
    """Tracks what has been processed to allow resume."""

    completed_files: set[str] = field(default_factory=set)
    failed_files: dict[str, str] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        data = {
            "completed": list(self.completed_files),
            "failed": self.failed_files,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> ProcessingState:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(
            completed_files=set(data.get("completed", [])),
            failed_files=data.get("failed", {}),
        )


class DocumentProcessor:
    """Process documents into text chunks ready for embedding.

    Features:
    - PDF text extraction via PyMuPDF (fitz)
    - Plain text / markdown file reading
    - Configurable chunk_size and overlap
    - Metadata extraction (filename, page, dates, document type)
    - Batch processing with parallel workers
    - Resume capability via ProcessingState
    - Per-document error handling (never fails entire batch)
    - Memory efficient: yields chunks via generator or processes in batches
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_workers: int | None = None,
        batch_size: int = 50,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_workers = max_workers or min(4, (os.cpu_count() or 1))
        self.batch_size = batch_size
        self._progress_callback: ProcessorProgressCallback | None = None
        self._cancelled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_progress_callback(self, callback: ProcessorProgressCallback) -> None:
        self._progress_callback = callback

    def cancel(self) -> None:
        self._cancelled = True

    def process_file(self, file_path: Path) -> ProcessedDocument:
        """Process a single file and return its chunks + metadata."""
        file_path = Path(file_path)
        filename = file_path.name

        try:
            if is_pdf(file_path):
                text, page_count = self._extract_pdf(file_path)
            else:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                page_count = 1

            doc_type = classify_document_type(filename, text)
            chunks = self._chunk_text(text, file_path, page_count, doc_type)

            return ProcessedDocument(
                source_path=str(file_path),
                filename=filename,
                chunks=chunks,
                page_count=page_count,
                total_chars=len(text),
                document_type=doc_type,
            )
        except Exception as exc:
            logger.error("Failed to process %s: %s", filename, exc)
            return ProcessedDocument(
                source_path=str(file_path),
                filename=filename,
                chunks=[],
                page_count=0,
                total_chars=0,
                document_type="unknown",
                error=str(exc),
            )

    def process_batch(
        self,
        files: list[Path],
        state_path: Path | None = None,
    ) -> Generator[ProcessedDocument, None, None]:
        """Process a list of files, yielding results one at a time.

        Uses a ProcessingState file for resume capability. Files already in
        state.completed_files are skipped.

        Yields ProcessedDocument objects (including those with errors).
        """
        self._cancelled = False
        state = ProcessingState.load(state_path) if state_path else ProcessingState()

        # Filter out already-completed files
        pending = [f for f in files if str(f) not in state.completed_files]
        total = len(files)
        done = total - len(pending)

        logger.info(
            "Processing batch: %d total, %d already done, %d pending",
            total, done, len(pending),
        )

        start_time = time.time()

        for idx, file_path in enumerate(pending, 1):
            if self._cancelled:
                logger.info("Processing cancelled at %d/%d", done + idx - 1, total)
                break

            current_name = file_path.name
            if self._progress_callback:
                self._progress_callback(done + idx, total, current_name, "processing")

            result = self.process_file(file_path)

            if result.error:
                state.failed_files[str(file_path)] = result.error
            else:
                state.completed_files.add(str(file_path))

            if state_path:
                state.save(state_path)

            yield result

        if self._progress_callback and not self._cancelled:
            self._progress_callback(total, total, "", "completed")

    def process_batch_parallel(
        self,
        files: list[Path],
        state_path: Path | None = None,
    ) -> Generator[ProcessedDocument, None, None]:
        """Process files using a process pool for CPU-bound PDF extraction.

        Falls back to sequential processing if the pool encounters issues.
        Yields ProcessedDocument objects.
        """
        self._cancelled = False
        state = ProcessingState.load(state_path) if state_path else ProcessingState()
        pending = [f for f in files if str(f) not in state.completed_files]
        total = len(files)
        done = total - len(pending)

        logger.info(
            "Parallel processing: %d total, %d pending, %d workers",
            total, len(pending), self.max_workers,
        )

        start_time = time.time()

        # Process in batches to keep memory bounded
        for batch_start in range(0, len(pending), self.batch_size):
            if self._cancelled:
                break

            batch = pending[batch_start : batch_start + self.batch_size]

            try:
                with ProcessPoolExecutor(max_workers=self.max_workers) as pool:
                    future_to_path = {
                        pool.submit(_process_file_worker, fp, self.chunk_size, self.chunk_overlap): fp
                        for fp in batch
                    }

                    for future in as_completed(future_to_path):
                        if self._cancelled:
                            pool.shutdown(wait=False, cancel_futures=True)
                            break

                        file_path = future_to_path[future]
                        done += 1

                        try:
                            result = future.result(timeout=120)
                        except Exception as exc:
                            result = ProcessedDocument(
                                source_path=str(file_path),
                                filename=file_path.name,
                                chunks=[],
                                page_count=0,
                                total_chars=0,
                                document_type="unknown",
                                error=str(exc),
                            )

                        if result.error:
                            state.failed_files[str(file_path)] = result.error
                        else:
                            state.completed_files.add(str(file_path))

                        if state_path:
                            state.save(state_path)

                        if self._progress_callback:
                            self._progress_callback(
                                done, total, file_path.name, "processing"
                            )

                        yield result

            except Exception as exc:
                logger.warning(
                    "Parallel batch failed (%s), falling back to sequential", exc
                )
                for fp in batch:
                    if self._cancelled:
                        break
                    if str(fp) in state.completed_files:
                        continue
                    done += 1
                    result = self.process_file(fp)
                    if result.error:
                        state.failed_files[str(fp)] = result.error
                    else:
                        state.completed_files.add(str(fp))
                    if state_path:
                        state.save(state_path)
                    if self._progress_callback:
                        self._progress_callback(done, total, fp.name, "processing")
                    yield result

        if self._progress_callback and not self._cancelled:
            self._progress_callback(total, total, "", "completed")

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_pdf(self, file_path: Path) -> tuple[str, int]:
        """Extract text from a PDF file using PyMuPDF. Returns (text, page_count)."""
        import fitz  # PyMuPDF

        pages_text: list[str] = []
        try:
            with fitz.open(str(file_path)) as doc:
                page_count = len(doc)
                for page in doc:
                    text = page.get_text("text")
                    if text.strip():
                        pages_text.append(text)
        except Exception as exc:
            raise RuntimeError(f"PDF extraction failed for {file_path.name}: {exc}") from exc

        return "\n\n".join(pages_text), page_count

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def _chunk_text(
        self,
        text: str,
        file_path: Path,
        page_count: int,
        doc_type: str,
    ) -> list[DocumentChunk]:
        """Split text into overlapping chunks with metadata."""
        if not text.strip():
            return []

        chunks: list[DocumentChunk] = []
        doc_id = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]

        # Estimate which page a character offset belongs to
        chars_per_page = max(len(text) // max(page_count, 1), 1)

        start = 0
        chunk_idx = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at a sentence/paragraph boundary
            if end < len(text):
                # Look for paragraph break first
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + self.chunk_size // 2:
                    end = para_break + 2
                else:
                    # Look for sentence end
                    for sep in (". ", ".\n", "? ", "! "):
                        sent_break = text.rfind(sep, start, end)
                        if sent_break > start + self.chunk_size // 2:
                            end = sent_break + len(sep)
                            break

            chunk_text = text[start:end].strip()
            if chunk_text:
                estimated_page = min(start // chars_per_page + 1, page_count)
                date_found = extract_date_from_text(chunk_text[:500])

                metadata = {
                    "source": file_path.name,
                    "source_path": str(file_path),
                    "page": estimated_page,
                    "total_pages": page_count,
                    "chunk_index": chunk_idx,
                    "document_type": doc_type,
                    "char_offset": start,
                }
                if date_found:
                    metadata["date_reference"] = date_found

                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        metadata=metadata,
                        chunk_index=chunk_idx,
                        document_id=doc_id,
                    )
                )
                chunk_idx += 1

            # Advance with overlap
            start = end - self.chunk_overlap
            if start <= (end - self.chunk_size):
                # Safety: always advance
                start = end

        return chunks


# ======================================================================
# Module-level worker function for ProcessPoolExecutor (must be picklable)
# ======================================================================

def _process_file_worker(
    file_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> ProcessedDocument:
    """Standalone function used by the process pool to process one file."""
    processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return processor.process_file(file_path)
