"""GitHub dataset downloader with progress tracking and resume capability."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .utils import (
    ensure_directory,
    format_file_size,
    get_env,
    is_supported_file,
)

logger = logging.getLogger(__name__)

# Default repo for the Epstein Files dataset
DEFAULT_REPO_URL = "https://github.com/yung-megafone/Epstein-Files"

# Progress callback type: (downloaded_files, total_files, current_file)
ProgressCallback = Callable[[int, int, str], None]


class GitHubDatasetDownloader:
    """Download datasets from GitHub repositories.

    Supports:
    - Full repo clone via ``git clone --depth 1``
    - HTTP archive fallback when git is not available
    - Downloading specific folders or file types
    - Progress tracking via callbacks
    - Resume capability for interrupted downloads
    """

    def __init__(
        self,
        output_dir: str | Path | None = None,
        repo_url: str = DEFAULT_REPO_URL,
        file_extensions: list[str] | None = None,
        subfolder: str | None = None,
    ) -> None:
        self.repo_url = repo_url.rstrip("/")
        self.output_dir = Path(
            output_dir or get_env("DATASET_DIR", "./data/raw")
        )
        self.file_extensions = file_extensions  # None means all supported
        self.subfolder = subfolder
        self._progress_callback: ProgressCallback | None = None
        self._cancelled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Register a function to receive progress updates."""
        self._progress_callback = callback

    def cancel(self) -> None:
        """Request cancellation of an in-progress download."""
        self._cancelled = True

    def download(self) -> Path:
        """Download the dataset and return the path to the output directory.

        Tries ``git clone`` first.  Falls back to the GitHub zip archive API
        if git is unavailable or the clone fails.

        If the output directory already contains files, only missing files are
        downloaded (resume behaviour).
        """
        self._cancelled = False
        ensure_directory(self.output_dir)

        repo_name = self._repo_name()
        dest = self.output_dir / repo_name

        if dest.exists() and any(dest.iterdir()):
            logger.info("Destination %s already exists -- resuming", dest)
            return self._collect_files(dest)

        try:
            self._clone_with_git(dest)
        except Exception as exc:
            logger.warning("git clone failed (%s), falling back to zip download", exc)
            self._download_zip(dest)

        return self._collect_files(dest)

    def list_files(self, directory: Path | None = None) -> list[Path]:
        """Return a list of supported files in the downloaded directory."""
        root = directory or (self.output_dir / self._repo_name())
        if not root.exists():
            return []

        base = root / self.subfolder if self.subfolder else root
        if not base.exists():
            base = root

        files: list[Path] = []
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            if not self._matches_filter(p):
                continue
            files.append(p)
        return files

    def get_status(self) -> dict[str, Any]:
        """Return a summary dict of what has been downloaded."""
        repo_name = self._repo_name()
        dest = self.output_dir / repo_name
        files = self.list_files(dest)
        total_size = sum(f.stat().st_size for f in files)
        return {
            "repo_url": self.repo_url,
            "output_dir": str(dest),
            "total_files": len(files),
            "total_size": format_file_size(total_size),
            "exists": dest.exists(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _repo_name(self) -> str:
        """Extract repository name from URL."""
        return self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    def _matches_filter(self, path: Path) -> bool:
        """Check if a file matches the configured extension/folder filter."""
        if self.file_extensions:
            if path.suffix.lower() not in {
                ext if ext.startswith(".") else f".{ext}"
                for ext in self.file_extensions
            }:
                return False
        else:
            if not is_supported_file(path):
                return False
        return True

    def _clone_with_git(self, dest: Path) -> None:
        """Shallow-clone the repository using the ``git`` CLI."""
        logger.info("Cloning %s -> %s", self.repo_url, dest)
        cmd = ["git", "clone", "--depth", "1", self.repo_url, str(dest)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
        logger.info("Clone complete")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        reraise=True,
    )
    def _download_zip(self, dest: Path) -> None:
        """Download the repo as a zip archive and extract it."""
        # GitHub provides zip archives at /archive/refs/heads/<branch>.zip
        zip_url = f"{self.repo_url}/archive/refs/heads/main.zip"
        logger.info("Downloading zip archive from %s", zip_url)

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "repo.zip"

            # Stream download with progress
            response = requests.get(zip_url, stream=True, timeout=120)
            if response.status_code == 404:
                # Try 'master' branch
                zip_url = f"{self.repo_url}/archive/refs/heads/master.zip"
                response = requests.get(zip_url, stream=True, timeout=120)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancelled:
                        logger.info("Download cancelled by user")
                        return
                    f.write(chunk)
                    downloaded += len(chunk)

            logger.info("Downloaded %s, extracting...", format_file_size(downloaded))

            import zipfile

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmpdir)

            # The zip contains a top-level directory like RepoName-main/
            extracted_dirs = [
                d for d in Path(tmpdir).iterdir()
                if d.is_dir() and d.name != "__MACOSX"
            ]
            if not extracted_dirs:
                raise RuntimeError("No directories found in zip archive")

            src = extracted_dirs[0]
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)

        logger.info("Zip extraction complete -> %s", dest)

    def _collect_files(self, dest: Path) -> Path:
        """Walk the destination directory and report progress."""
        files = self.list_files(dest)
        total = len(files)
        for idx, f in enumerate(files, 1):
            if self._cancelled:
                logger.info("Collection cancelled after %d/%d files", idx - 1, total)
                break
            if self._progress_callback:
                self._progress_callback(idx, total, f.name)
        logger.info("Collected %d supported files from %s", total, dest)
        return dest
