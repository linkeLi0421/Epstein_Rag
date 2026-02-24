"""One-step data preparation: download DOJ Epstein dataset ZIPs, extract PDFs, index into ChromaDB.

Usage (inside Docker):
    python -m services.data_prep --datasets 5 6 7 12
    python -m services.data_prep --datasets all-small   # datasets 1-7 + 12 (~2.1 GB)
    python -m services.data_prep --datasets 12           # just dataset 12 (114 MB, quick test)

This script:
1. Downloads dataset ZIP files from Internet Archive mirrors (more reliable than DOJ)
2. Extracts PDF files from the ZIPs
3. Runs the indexing pipeline to process PDFs and push chunks into ChromaDB
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

from .pipeline import Pipeline
from .utils import ensure_directory, get_env

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dataset registry — sizes and download URLs with SHA256 hashes
# ---------------------------------------------------------------------------

def _geeken(n: int) -> str:
    return f"https://doj-files.geeken.dev/doj_zips/original_archives/DataSet%20{n}.zip"


DATASETS: dict[int, dict] = {
    1: {
        "size": "1.23 GB",
        "urls": [_geeken(1), "https://archive.org/download/data-set-1/DataSet%201.zip"],
        "sha256": "598f4d2d71f0d183cf898cd9d6fb8ec1f6161e0e71d8c37897936aef75f860b4",
    },
    2: {
        "size": "630 MB",
        "urls": [_geeken(2), "https://archive.org/download/data-set-1/DataSet%202.zip"],
        "sha256": "24cebbaefe9d49bca57726b5a4b531ff20e6a97c370ba87a7593dd8dbdb77bff",
    },
    3: {
        "size": "595 MB",
        "urls": [_geeken(3), "https://archive.org/download/data-set-1/DataSet%203.zip"],
        "sha256": "160231c8c689c76003976b609e55689530fc4832a1535ce13bfcd8f871c21e65",
    },
    4: {
        "size": "351 MB",
        "urls": [_geeken(4), "https://archive.org/download/data-set-1/DataSet%204.zip"],
        "sha256": "979154842bac356ef36bb2d0e72f78e0f6b771d79e02dd6934cff699944e2b71",
    },
    5: {
        "size": "61.4 MB",
        "urls": [_geeken(5), "https://archive.org/download/data-set-1/DataSet%205.zip"],
        "sha256": "7317e2ad089c82a59378a9c038e964feab246be62ecc24663b741617af3da709",
    },
    6: {
        "size": "51.2 MB",
        "urls": [_geeken(6), "https://archive.org/download/data-set-1/DataSet%206.zip"],
        "sha256": "d54d26d94127b9a277cf3f7d9eeaf9a7271f118757997edac3bc6e1039ed6555",
    },
    7: {
        "size": "96.9 MB",
        "urls": [_geeken(7), "https://archive.org/download/data-set-1/DataSet%207.zip"],
        "sha256": "51e1961b3bcf18a21afd9bcf697fdb54dac97d1b64cf88297f4c5be268d26b8e",
    },
    12: {
        "size": "114 MB",
        "urls": [_geeken(12), "https://archive.org/download/data-set-12_202601/DataSet%2012.zip"],
        "sha256": "b5314b7efca98e25d8b35e4b7fac3ebb3ca2e6cfd0937aa2300ca8b71543bbe2",
    },
}

# Presets
PRESET_SMALL = [5, 6, 7, 12]          # ~323 MB
PRESET_ALL_SMALL = [1, 2, 3, 4, 5, 6, 7, 12]  # ~2.1 GB (skip 8-11 which are 10-180 GB)


def download_file(url: str, dest: Path, expected_sha256: str | None = None) -> bool:
    """Download a file with progress bar. Returns True on success."""
    logger.info("Downloading %s", url)
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Download failed from %s: %s", url, exc)
        return False

    total = int(resp.headers.get("content-length", 0))
    sha = hashlib.sha256()

    with open(dest, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, desc=dest.name
    ) as pbar:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            sha.update(chunk)
            pbar.update(len(chunk))

    if expected_sha256:
        actual = sha.hexdigest().lower()
        expected = expected_sha256.lower()
        if actual != expected:
            logger.warning(
                "SHA256 mismatch for %s: expected %s, got %s",
                dest.name, expected[:16] + "...", actual[:16] + "...",
            )
            # Don't fail — hash variants exist between DOJ/archive copies

    return True


def download_dataset(ds_num: int, download_dir: Path) -> Path | None:
    """Download a single dataset ZIP, trying mirrors in order. Returns path or None."""
    info = DATASETS.get(ds_num)
    if not info:
        logger.error("Unknown dataset: %d (available: %s)", ds_num, sorted(DATASETS.keys()))
        return None

    zip_name = f"DataSet_{ds_num}.zip"
    zip_path = download_dir / zip_name

    if zip_path.exists():
        logger.info("Dataset %d already downloaded: %s", ds_num, zip_path)
        return zip_path

    for url in info["urls"]:
        if download_file(url, zip_path, info.get("sha256")):
            return zip_path

    logger.error("All download sources failed for Dataset %d", ds_num)
    return None


def extract_pdfs(zip_path: Path, output_dir: Path) -> int:
    """Extract PDF files from a ZIP archive. Returns count of extracted PDFs."""
    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.filename.lower().endswith(".pdf"):
                # Flatten directory structure — extract to output_dir directly
                filename = Path(info.filename).name
                target = output_dir / filename
                if target.exists():
                    continue
                with zf.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Download, extract, and index Epstein DOJ dataset PDFs"
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["12"],
        help=(
            "Dataset numbers to download (e.g., 5 6 7 12), "
            "or presets: 'small' (5,6,7,12 ~323MB), "
            "'all-small' (1-7+12 ~2.1GB). Default: 12"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for extracted PDFs (default: ./data/raw/epstein_pdfs or DATASET_DIR env)",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Only download and extract, don't run the indexing pipeline",
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

    # Parse dataset selection
    selected: list[int] = []
    for ds in args.datasets:
        if ds == "small":
            selected.extend(PRESET_SMALL)
        elif ds == "all-small":
            selected.extend(PRESET_ALL_SMALL)
        else:
            try:
                selected.append(int(ds))
            except ValueError:
                logger.error("Invalid dataset: %s", ds)
                sys.exit(1)
    selected = sorted(set(selected))

    total_size = ", ".join(f"DS{n} ({DATASETS[n]['size']})" for n in selected if n in DATASETS)
    logger.info("Selected datasets: %s", total_size)

    # Directories
    base_dir = Path(args.output_dir or get_env("DATASET_DIR", "./data/raw"))
    download_dir = base_dir / "zips"
    pdf_dir = base_dir / "epstein_pdfs"
    ensure_directory(download_dir)
    ensure_directory(pdf_dir)

    # Phase 1: Download
    logger.info("=== Phase 1: Download ZIPs ===")
    zip_files: list[Path] = []
    for ds_num in selected:
        zip_path = download_dataset(ds_num, download_dir)
        if zip_path:
            zip_files.append(zip_path)
        else:
            logger.warning("Skipping dataset %d (download failed)", ds_num)

    if not zip_files:
        logger.error("No datasets downloaded successfully")
        sys.exit(1)

    # Phase 2: Extract PDFs
    logger.info("=== Phase 2: Extract PDFs ===")
    total_pdfs = 0
    for zp in zip_files:
        logger.info("Extracting PDFs from %s...", zp.name)
        count = extract_pdfs(zp, pdf_dir)
        total_pdfs += count
        logger.info("  Extracted %d PDFs", count)

    existing_pdfs = list(pdf_dir.glob("*.pdf"))
    logger.info("Total PDFs in %s: %d", pdf_dir, len(existing_pdfs))

    if not existing_pdfs:
        logger.error("No PDFs found after extraction")
        sys.exit(1)

    if args.skip_index:
        logger.info("Skipping indexing (--skip-index)")
        print(f"\nData ready at: {pdf_dir}")
        print(f"Total PDFs: {len(existing_pdfs)}")
        print("Run the pipeline separately to index.")
        sys.exit(0)

    # Phase 3: Index
    logger.info("=== Phase 3: Index into ChromaDB ===")
    pipeline = Pipeline(
        repo_url="epstein-doj-datasets",
        output_dir=str(pdf_dir),
    )

    # Override the download step — data is already prepared
    # Run processing + indexing directly
    import asyncio
    import time
    import uuid
    from datetime import datetime, timezone

    from .document_processor import DocumentProcessor

    async def run_indexing():
        start_time = time.time()
        pipeline._job_id = str(uuid.uuid4())
        await pipeline._update_job(
            status="processing",
            started_at=datetime.now(timezone.utc),
        )

        processor = DocumentProcessor(
            chunk_size=pipeline.chunk_size,
            chunk_overlap=pipeline.chunk_overlap,
            max_workers=pipeline.max_workers,
            batch_size=pipeline.batch_size,
        )

        files = sorted(pdf_dir.glob("*.pdf"))
        total_files = len(files)
        await pipeline._update_job(total_files=total_files)
        logger.info("Processing %d PDF files...", total_files)

        all_chunks = []
        processed_count = 0
        failed_count = 0

        for doc in processor.process_batch_parallel(files):
            if doc.error:
                failed_count += 1
                logger.warning("Failed: %s -- %s", doc.filename, doc.error)
            else:
                processed_count += 1
                all_chunks.extend(doc.chunks)

            progress = int(((processed_count + failed_count) / total_files) * 100)
            await pipeline._update_job(
                processed_files=processed_count,
                failed_files=failed_count,
                progress_percent=min(progress, 99),
                current_file=doc.filename,
            )

        logger.info("=== Indexing %d chunks into ChromaDB ===", len(all_chunks))
        await pipeline._update_job(current_file="Indexing into vector store...")
        indexed = await pipeline._index_chunks(all_chunks)

        elapsed = time.time() - start_time
        await pipeline._update_job(
            status="completed",
            progress_percent=100,
            current_file="",
            completed_at=datetime.now(timezone.utc),
        )

        return {
            "total_files": total_files,
            "processed_files": processed_count,
            "failed_files": failed_count,
            "total_chunks": len(all_chunks),
            "indexed_chunks": indexed,
            "elapsed_seconds": round(elapsed, 1),
        }

    summary = asyncio.run(run_indexing())

    print("\n" + "=" * 60)
    print("Data Preparation Complete")
    print("=" * 60)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print("=" * 60)

    sys.exit(0 if summary["indexed_chunks"] > 0 else 1)


if __name__ == "__main__":
    main()
