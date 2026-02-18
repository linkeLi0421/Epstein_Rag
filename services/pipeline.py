"""End-to-end pipeline: download -> process -> index.

Orchestrates the dataset downloader and document processor, pushes chunks
into ChromaDB for vector search, and reports progress to the IndexingJob
table in PostgreSQL.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset_downloader import GitHubDatasetDownloader
from .document_processor import DocumentChunk, DocumentProcessor
from .utils import ensure_directory, estimate_eta, get_env

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrate download -> process -> index with progress tracking.

    Configuration is read from environment variables with sensible defaults:

    - ``DATABASE_URL``: PostgreSQL connection string
    - ``CHROMA_HOST`` / ``CHROMA_PORT``: ChromaDB location
    - ``CHROMA_COLLECTION``: collection name (default ``epstein_documents``)
    - ``DATASET_DIR``: where raw downloads are stored (default ``./data/raw``)
    - ``STATE_DIR``: where processing state is persisted (default ``./data/state``)
    - ``CHUNK_SIZE`` / ``CHUNK_OVERLAP``: chunking parameters
    - ``MAX_WORKERS``: parallel processing workers
    - ``BATCH_SIZE``: documents per processing batch
    """

    def __init__(
        self,
        repo_url: str = "https://github.com/yung-megafone/Epstein-Files",
        output_dir: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        max_workers: int | None = None,
        batch_size: int | None = None,
        chroma_host: str | None = None,
        chroma_port: int | None = None,
        chroma_collection: str | None = None,
        database_url: str | None = None,
    ) -> None:
        self.repo_url = repo_url

        # Directories
        self.output_dir = Path(output_dir or get_env("DATASET_DIR", "./data/raw"))
        self.state_dir = Path(get_env("STATE_DIR", "./data/state"))
        ensure_directory(self.state_dir)

        # Processing params
        self.chunk_size = chunk_size or int(get_env("CHUNK_SIZE", "1000"))
        self.chunk_overlap = chunk_overlap or int(get_env("CHUNK_OVERLAP", "200"))
        self.max_workers = max_workers or int(get_env("MAX_WORKERS", "4"))
        self.batch_size = batch_size or int(get_env("BATCH_SIZE", "50"))

        # ChromaDB
        self.chroma_host = chroma_host or get_env("CHROMA_HOST", "localhost")
        self.chroma_port = chroma_port or int(get_env("CHROMA_PORT", "8000"))
        self.chroma_collection = chroma_collection or get_env(
            "CHROMA_COLLECTION", "epstein_documents"
        )

        # Database
        self.database_url = database_url or get_env(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/epstein_rag",
        )

        # Internal state
        self._job_id: str | None = None
        self._cancelled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, parallel: bool = True) -> dict[str, Any]:
        """Run the full pipeline synchronously. Returns a summary dict."""
        return asyncio.run(self.run_async(parallel=parallel))

    async def run_async(self, parallel: bool = True) -> dict[str, Any]:
        """Run the full pipeline with async DB updates."""
        start_time = time.time()
        self._cancelled = False

        # Create an IndexingJob record
        self._job_id = str(uuid.uuid4())
        await self._update_job(
            status="processing",
            started_at=datetime.now(timezone.utc),
        )

        summary: dict[str, Any] = {
            "job_id": self._job_id,
            "repo_url": self.repo_url,
            "status": "processing",
        }

        try:
            # Phase 1: Download
            logger.info("=== Phase 1: Download ===")
            await self._update_job(current_file="Downloading repository...")

            downloader = GitHubDatasetDownloader(
                output_dir=self.output_dir,
                repo_url=self.repo_url,
            )
            dest_dir = downloader.download()
            files = downloader.list_files(dest_dir)

            if not files:
                await self._update_job(
                    status="failed",
                    error_message="No supported files found in repository",
                    completed_at=datetime.now(timezone.utc),
                )
                summary["status"] = "failed"
                summary["error"] = "No supported files found"
                return summary

            total_files = len(files)
            await self._update_job(total_files=total_files)
            logger.info("Found %d files to process", total_files)

            # Phase 2: Process
            logger.info("=== Phase 2: Process ===")
            processor = DocumentProcessor(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                max_workers=self.max_workers,
                batch_size=self.batch_size,
            )

            state_path = self.state_dir / f"{self._job_id}.json"

            all_chunks: list[DocumentChunk] = []
            processed_count = 0
            failed_count = 0

            process_fn = (
                processor.process_batch_parallel if parallel else processor.process_batch
            )

            for doc in process_fn(files, state_path=state_path):
                if self._cancelled:
                    break

                if doc.error:
                    failed_count += 1
                    logger.warning("Failed: %s -- %s", doc.filename, doc.error)
                else:
                    processed_count += 1
                    all_chunks.extend(doc.chunks)

                progress = int(
                    ((processed_count + failed_count) / total_files) * 100
                )
                await self._update_job(
                    processed_files=processed_count,
                    failed_files=failed_count,
                    progress_percent=min(progress, 99),
                    current_file=doc.filename,
                )

            if self._cancelled:
                await self._update_job(
                    status="failed",
                    error_message="Cancelled by user",
                    completed_at=datetime.now(timezone.utc),
                )
                summary["status"] = "cancelled"
                return summary

            # Phase 3: Index into ChromaDB
            logger.info("=== Phase 3: Index (%d chunks) ===", len(all_chunks))
            await self._update_job(current_file="Indexing into vector store...")
            indexed = await self._index_chunks(all_chunks)

            elapsed = time.time() - start_time

            await self._update_job(
                status="completed",
                progress_percent=100,
                current_file="",
                completed_at=datetime.now(timezone.utc),
            )

            summary.update(
                {
                    "status": "completed",
                    "total_files": total_files,
                    "processed_files": processed_count,
                    "failed_files": failed_count,
                    "total_chunks": len(all_chunks),
                    "indexed_chunks": indexed,
                    "elapsed_seconds": round(elapsed, 1),
                }
            )
            logger.info("Pipeline complete: %s", summary)
            return summary

        except Exception as exc:
            logger.exception("Pipeline failed")
            await self._update_job(
                status="failed",
                error_message=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            summary["status"] = "failed"
            summary["error"] = str(exc)
            return summary

    def cancel(self) -> None:
        """Request cancellation of a running pipeline."""
        self._cancelled = True

    # ------------------------------------------------------------------
    # ChromaDB indexing
    # ------------------------------------------------------------------

    async def _index_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Add document chunks to ChromaDB. Returns count of indexed chunks."""
        if not chunks:
            return 0

        try:
            import chromadb

            client = chromadb.HttpClient(
                host=self.chroma_host, port=self.chroma_port
            )
            collection = client.get_or_create_collection(
                name=self.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )

            # Index in batches to avoid oversized requests
            index_batch_size = 100
            indexed = 0

            for i in range(0, len(chunks), index_batch_size):
                if self._cancelled:
                    break

                batch = chunks[i : i + index_batch_size]
                ids = [
                    f"{c.document_id}_{c.chunk_index}" for c in batch
                ]
                documents = [c.text for c in batch]
                metadatas = [c.metadata for c in batch]

                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                indexed += len(batch)

                logger.info(
                    "Indexed %d/%d chunks", indexed, len(chunks)
                )

            return indexed

        except Exception as exc:
            logger.error("ChromaDB indexing failed: %s", exc)
            logger.info(
                "Chunks were processed successfully but not indexed. "
                "Ensure ChromaDB is running at %s:%s",
                self.chroma_host,
                self.chroma_port,
            )
            return 0

    # ------------------------------------------------------------------
    # PostgreSQL job tracking
    # ------------------------------------------------------------------

    async def _update_job(self, **kwargs: Any) -> None:
        """Update the IndexingJob record in PostgreSQL.

        Silently logs errors if the database is unreachable (the pipeline
        should still complete even without DB connectivity).
        """
        if not self._job_id:
            return

        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(self.database_url, echo=False)

            # Build SET clause dynamically
            set_parts: list[str] = []
            params: dict[str, Any] = {"job_id": self._job_id}

            for key, value in kwargs.items():
                set_parts.append(f"{key} = :{key}")
                params[key] = value

            if not set_parts:
                await engine.dispose()
                return

            # Upsert: INSERT on first call, UPDATE on subsequent
            # Try UPDATE first; if no rows affected, INSERT
            update_sql = text(
                f"UPDATE indexing_jobs SET {', '.join(set_parts)} WHERE id = :job_id"
            )
            insert_cols = ["id", "source_type", "source_url"] + list(kwargs.keys())
            insert_params = {
                "job_id": self._job_id,
                "source_type": "github",
                "source_url": self.repo_url,
                **kwargs,
            }

            async with engine.begin() as conn:
                result = await conn.execute(update_sql, params)
                if result.rowcount == 0:
                    # First time -- insert
                    cols = ", ".join(
                        ["id", "source_type", "source_url"]
                        + [k for k in kwargs.keys()]
                    )
                    placeholders = ", ".join(
                        [":job_id", ":source_type", ":source_url"]
                        + [f":{k}" for k in kwargs.keys()]
                    )
                    insert_sql = text(
                        f"INSERT INTO indexing_jobs ({cols}) VALUES ({placeholders})"
                    )
                    await conn.execute(insert_sql, insert_params)

            await engine.dispose()

        except Exception as exc:
            # Non-fatal: log and continue
            logger.debug("Could not update IndexingJob in DB: %s", exc)


# ======================================================================
# CLI entry point
# ======================================================================

def main() -> None:
    """CLI interface for running the data pipeline."""
    parser = argparse.ArgumentParser(
        description="Epstein RAG Data Pipeline - download, process, and index documents"
    )
    parser.add_argument(
        "--repo-url",
        default="https://github.com/yung-megafone/Epstein-Files",
        help="GitHub repository URL to download",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to store downloaded files (default: ./data/raw or DATASET_DIR env)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Text chunk size in characters (default: 1000 or CHUNK_SIZE env)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Overlap between chunks in characters (default: 200 or CHUNK_OVERLAP env)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Number of parallel workers (default: 4 or MAX_WORKERS env)",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Disable parallel processing (useful for debugging)",
    )
    parser.add_argument(
        "--chroma-host",
        default=None,
        help="ChromaDB host (default: localhost or CHROMA_HOST env)",
    )
    parser.add_argument(
        "--chroma-port",
        type=int,
        default=None,
        help="ChromaDB port (default: 8000 or CHROMA_PORT env)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL connection URL (default from DATABASE_URL env)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    pipeline = Pipeline(
        repo_url=args.repo_url,
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_workers=args.max_workers,
        chroma_host=args.chroma_host,
        chroma_port=args.chroma_port,
        database_url=args.database_url,
    )

    summary = pipeline.run(parallel=not args.sequential)

    print("\n" + "=" * 60)
    print("Pipeline Summary")
    print("=" * 60)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print("=" * 60)

    sys.exit(0 if summary.get("status") == "completed" else 1)


if __name__ == "__main__":
    main()
