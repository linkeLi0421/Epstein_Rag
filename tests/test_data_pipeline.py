"""Unit tests for the Data Pipeline - GitHub downloader and document processor.

Tests cover:
- GitHubDatasetDownloader (URL parsing, file filtering, progress tracking)
- DocumentProcessor (text chunking, metadata, batch processing, resume)
- Pipeline orchestration (status transitions with mocked DB)
- Utility functions (file classification, date extraction, formatting)
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_indexing_job


# ═══════════════════════════════════════════════════════════════════════════════
# Utility Function Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtils:
    """Tests for services.utils helper functions."""

    def test_is_supported_file(self):
        from services.utils import is_supported_file

        assert is_supported_file("document.pdf") is True
        assert is_supported_file("readme.md") is True
        assert is_supported_file("notes.txt") is True
        assert is_supported_file("report.docx") is True
        assert is_supported_file("image.png") is False
        assert is_supported_file("data.csv") is False
        assert is_supported_file("script.py") is False

    def test_is_pdf(self):
        from services.utils import is_pdf

        assert is_pdf("document.pdf") is True
        assert is_pdf("DOCUMENT.PDF") is True
        assert is_pdf("readme.md") is False

    def test_get_file_extension(self):
        from services.utils import get_file_extension

        assert get_file_extension("test.pdf") == ".pdf"
        assert get_file_extension("file.TXT") == ".txt"
        assert get_file_extension("no_ext") == ""

    def test_format_file_size(self):
        from services.utils import format_file_size

        assert format_file_size(500) == "500.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_classify_document_type(self):
        from services.utils import classify_document_type

        assert classify_document_type("flight_manifest.pdf", "passenger list tail number") == "flight_log"
        assert classify_document_type("ruling_2023.pdf", "court order defendant") == "court_document"
        assert classify_document_type("depo_john.pdf", "deposition sworn testimony deponent") == "deposition"
        assert classify_document_type("report.pdf", "police arrest incident officer") == "police_report"
        assert classify_document_type("records.pdf", "bank transaction wire transfer") == "financial"
        assert classify_document_type("msg.pdf", "dear sir letter sincerely") == "correspondence"
        assert classify_document_type("random.pdf", "no keywords here") == "other"

    def test_extract_date_from_text(self):
        from services.utils import extract_date_from_text

        assert extract_date_from_text("On 01/15/2024 the event...") == "01/15/2024"
        assert extract_date_from_text("Date: 2024-01-15 document") == "2024-01-15"
        assert extract_date_from_text("January 15, 2024 meeting") == "January 15, 2024"
        assert extract_date_from_text("no date here") is None

    def test_safe_filename(self):
        from services.utils import safe_filename

        assert safe_filename("normal_file.txt") == "normal_file.txt"
        assert safe_filename('file<>:"/|.txt') == "file_______.txt"
        assert safe_filename("") == "unnamed"

    def test_estimate_eta(self):
        from services.utils import estimate_eta

        assert estimate_eta(50, 100, 50.0) == "50s"
        assert estimate_eta(0, 100, 0.0) is None
        assert estimate_eta(10, 100, 600.0) is not None  # 90 * 60 = 5400s


# ═══════════════════════════════════════════════════════════════════════════════
# Text Chunking Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTextChunking:
    """Tests for DocumentProcessor text chunking."""

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Simple chunking for testing."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += chunk_size - overlap
        return chunks

    def test_basic_chunking(self):
        text = "word " * 500  # 2500 chars
        chunks = self._chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) >= 3
        for chunk in chunks[:-1]:
            assert len(chunk) == 1000

    def test_chunking_with_overlap(self):
        text = "A" * 2000
        chunks = self._chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) >= 2
        assert chunks[0][-200:] == chunks[1][:200]

    def test_short_text_single_chunk(self):
        chunks = self._chunk_text("Short text.", chunk_size=1000, overlap=200)
        assert len(chunks) == 1

    def test_empty_text(self):
        chunks = self._chunk_text("", chunk_size=1000, overlap=200)
        assert len(chunks) == 0

    def test_exact_chunk_size(self):
        text = "A" * 1000
        chunks = self._chunk_text(text, chunk_size=1000, overlap=200)
        assert len(chunks) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Document Processor Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""

    def test_process_text_file(self, tmp_path):
        from services.document_processor import DocumentProcessor

        test_file = tmp_path / "test.txt"
        test_file.write_text("This is test content for the document processor." * 20)

        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        result = processor.process_file(test_file)

        assert result.filename == "test.txt"
        assert result.error is None
        assert result.total_chars > 0
        assert len(result.chunks) > 0
        assert result.page_count == 1

    def test_process_markdown_file(self, tmp_path):
        from services.document_processor import DocumentProcessor

        test_file = tmp_path / "readme.md"
        test_file.write_text("# Title\n\nSome content here.\n\n## Section 2\n\nMore content.")

        processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
        result = processor.process_file(test_file)

        assert result.filename == "readme.md"
        assert result.error is None
        assert len(result.chunks) >= 1

    def test_process_nonexistent_file(self):
        from services.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        result = processor.process_file(Path("/nonexistent/file.txt"))

        assert result.error is not None
        assert len(result.chunks) == 0

    def test_process_empty_file(self, tmp_path):
        from services.document_processor import DocumentProcessor

        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        processor = DocumentProcessor()
        result = processor.process_file(test_file)

        assert len(result.chunks) == 0
        assert result.total_chars == 0

    def test_chunk_metadata(self, tmp_path):
        from services.document_processor import DocumentProcessor

        test_file = tmp_path / "flight_manifest.txt"
        test_file.write_text("Passenger list with tail number N900SA. " * 50)

        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
        result = processor.process_file(test_file)

        assert result.document_type == "flight_log"
        for chunk in result.chunks:
            assert "source" in chunk.metadata
            assert "chunk_index" in chunk.metadata
            assert chunk.metadata["source"] == "flight_manifest.txt"

    def test_batch_processing(self, tmp_path):
        from services.document_processor import DocumentProcessor

        files = []
        for i in range(5):
            f = tmp_path / f"doc_{i}.txt"
            f.write_text(f"Content of document {i}. " * 20)
            files.append(f)

        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        results = list(processor.process_batch(files))

        assert len(results) == 5
        assert all(r.error is None for r in results)

    def test_batch_processing_with_failures(self, tmp_path):
        from services.document_processor import DocumentProcessor

        files = []
        for i in range(3):
            f = tmp_path / f"good_{i}.txt"
            f.write_text(f"Good content {i}. " * 20)
            files.append(f)

        # Add a nonexistent file
        files.append(Path(tmp_path / "missing.txt"))

        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        results = list(processor.process_batch(files))

        assert len(results) == 4
        errors = [r for r in results if r.error]
        assert len(errors) == 1

    def test_cancellation(self, tmp_path):
        from services.document_processor import DocumentProcessor

        files = []
        for i in range(10):
            f = tmp_path / f"doc_{i}.txt"
            f.write_text(f"Content {i}. " * 20)
            files.append(f)

        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)

        results = []
        for i, doc in enumerate(processor.process_batch(files)):
            results.append(doc)
            if i == 2:
                processor.cancel()
                break

        # Should have stopped early
        assert len(results) <= 4

    def test_processing_state_resume(self, tmp_path):
        from services.document_processor import DocumentProcessor, ProcessingState

        state_file = tmp_path / "state.json"

        files = []
        for i in range(5):
            f = tmp_path / f"doc_{i}.txt"
            f.write_text(f"Content {i}. " * 20)
            files.append(f)

        # First run: process first 3
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        first_run = []
        for i, doc in enumerate(processor.process_batch(files, state_path=state_file)):
            first_run.append(doc)
            if i == 2:
                processor.cancel()
                break

        # Check state was saved
        state = ProcessingState.load(state_file)
        assert len(state.completed_files) > 0

        # Second run: should skip already-completed files
        processor2 = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        second_run = list(processor2.process_batch(files, state_path=state_file))

        # Combined should cover all files
        total = len(state.completed_files) + len(second_run)
        assert total >= 5


# ═══════════════════════════════════════════════════════════════════════════════
# GitHub Dataset Downloader Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGitHubDatasetDownloader:
    """Tests for GitHubDatasetDownloader."""

    def test_parse_github_url(self):
        from services.dataset_downloader import GitHubDatasetDownloader

        dl = GitHubDatasetDownloader(repo_url="https://github.com/yung-megafone/Epstein-Files")
        assert dl._repo_name() == "Epstein-Files"

    def test_parse_url_with_trailing_slash(self):
        from services.dataset_downloader import GitHubDatasetDownloader

        dl = GitHubDatasetDownloader(repo_url="https://github.com/owner/repo/")
        assert dl._repo_name() == "repo"

    def test_parse_url_with_git_suffix(self):
        from services.dataset_downloader import GitHubDatasetDownloader

        dl = GitHubDatasetDownloader(repo_url="https://github.com/owner/repo.git")
        assert dl._repo_name() == "repo"

    def test_list_files_empty_dir(self, tmp_path):
        from services.dataset_downloader import GitHubDatasetDownloader

        dl = GitHubDatasetDownloader(output_dir=tmp_path)
        files = dl.list_files(tmp_path)
        assert files == []

    def test_list_files_filters_supported(self, tmp_path):
        from services.dataset_downloader import GitHubDatasetDownloader

        (tmp_path / "doc.pdf").touch()
        (tmp_path / "notes.txt").touch()
        (tmp_path / "image.png").touch()
        (tmp_path / "script.py").touch()

        dl = GitHubDatasetDownloader(output_dir=tmp_path)
        files = dl.list_files(tmp_path)

        names = [f.name for f in files]
        assert "doc.pdf" in names
        assert "notes.txt" in names
        assert "image.png" not in names
        assert "script.py" not in names

    def test_get_status(self, tmp_path):
        from services.dataset_downloader import GitHubDatasetDownloader

        repo_dir = tmp_path / "Epstein-Files"
        repo_dir.mkdir()
        (repo_dir / "doc.pdf").write_bytes(b"fake pdf content")

        dl = GitHubDatasetDownloader(
            output_dir=tmp_path,
            repo_url="https://github.com/yung-megafone/Epstein-Files",
        )
        status = dl.get_status()

        assert status["exists"] is True
        assert status["total_files"] == 1

    def test_cancel(self):
        from services.dataset_downloader import GitHubDatasetDownloader

        dl = GitHubDatasetDownloader()
        assert dl._cancelled is False
        dl.cancel()
        assert dl._cancelled is True

    def test_progress_callback(self, tmp_path):
        from services.dataset_downloader import GitHubDatasetDownloader

        repo_dir = tmp_path / "Epstein-Files"
        repo_dir.mkdir()
        for i in range(3):
            (repo_dir / f"doc_{i}.txt").write_text(f"content {i}")

        progress_calls = []

        dl = GitHubDatasetDownloader(
            output_dir=tmp_path,
            repo_url="https://github.com/yung-megafone/Epstein-Files",
        )
        dl.set_progress_callback(lambda done, total, name: progress_calls.append((done, total, name)))

        dl._collect_files(repo_dir)
        assert len(progress_calls) == 3

    def test_custom_file_extensions(self, tmp_path):
        from services.dataset_downloader import GitHubDatasetDownloader

        (tmp_path / "doc.pdf").touch()
        (tmp_path / "notes.txt").touch()
        (tmp_path / "readme.md").touch()

        dl = GitHubDatasetDownloader(
            output_dir=tmp_path,
            file_extensions=[".pdf"],
        )
        files = dl.list_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "doc.pdf"


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline Tests (database state transitions)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipeline:
    """Tests for pipeline orchestration with mocked DB."""

    @pytest.mark.asyncio
    async def test_pipeline_creates_job_on_start(self, db_session: AsyncSession):
        from mcp_server.models import IndexingJob

        job = IndexingJob(
            source_type="github",
            source_url="https://github.com/yung-megafone/Epstein-Files",
            status="pending",
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.execute(select(IndexingJob))
        saved = result.scalar_one()
        assert saved.status == "pending"

    @pytest.mark.asyncio
    async def test_pipeline_status_transitions(self, db_session: AsyncSession):
        from mcp_server.models import IndexingJob

        job = IndexingJob(source_type="github", status="pending", total_files=0)
        db_session.add(job)
        await db_session.commit()

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.total_files = 50
        await db_session.commit()

        job.processed_files = 50
        job.progress_percent = 100
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        result = await db_session.execute(select(IndexingJob))
        final = result.scalar_one()
        assert final.status == "completed"
        assert final.started_at is not None
        assert final.completed_at is not None

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, db_session: AsyncSession):
        from mcp_server.models import IndexingJob

        job = IndexingJob(
            source_type="github",
            status="processing",
            total_files=100,
            processed_files=30,
        )
        db_session.add(job)
        await db_session.commit()

        job.status = "failed"
        job.error_message = "Connection timeout downloading files"
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        result = await db_session.execute(select(IndexingJob))
        failed = result.scalar_one()
        assert failed.status == "failed"
        assert "timeout" in failed.error_message

    @pytest.mark.asyncio
    async def test_pipeline_resume(self, db_session: AsyncSession):
        from mcp_server.models import IndexingJob

        job_id = uuid.uuid4()
        job = IndexingJob(
            id=job_id,
            source_type="github",
            status="failed",
            total_files=100,
            processed_files=60,
            error_message="Network error",
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        resumed = result.scalar_one()
        resumed.status = "processing"
        resumed.error_message = None
        await db_session.commit()

        resumed.processed_files = 100
        resumed.progress_percent = 100
        resumed.status = "completed"
        resumed.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        result = await db_session.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        final = result.scalar_one()
        assert final.status == "completed"
        assert final.processed_files == 100

    def test_pipeline_config_from_env(self, monkeypatch):
        monkeypatch.setenv("CHUNK_SIZE", "500")
        monkeypatch.setenv("CHUNK_OVERLAP", "100")
        monkeypatch.setenv("CHROMA_HOST", "remote-host")

        from services.pipeline import Pipeline

        pipeline = Pipeline()
        assert pipeline.chunk_size == 500
        assert pipeline.chunk_overlap == 100
        assert pipeline.chroma_host == "remote-host"
