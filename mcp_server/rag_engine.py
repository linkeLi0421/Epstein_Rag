"""RAG engine using ChromaDB for vector storage and sentence-transformers for embeddings."""

import hashlib
import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from .config import config

logger = logging.getLogger(__name__)


class RAGEngine:
    """Handles document indexing, embedding, and retrieval via ChromaDB."""

    def __init__(self):
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None
        self._model: SentenceTransformer | None = None

    # -- Lazy initialisation --------------------------------------------------

    def _get_client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.HttpClient(
                host=config.chroma_host,
                port=config.chroma_port,
            )
            logger.info(
                "Connected to ChromaDB at %s:%s",
                config.chroma_host,
                config.chroma_port,
            )
        return self._client

    def _get_collection(self) -> chromadb.Collection:
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=config.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Using collection '%s'", config.chroma_collection)
        return self._collection

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(config.embedding_model)
            logger.info("Loaded embedding model '%s'", config.embedding_model)
        return self._model

    # -- Text chunking --------------------------------------------------------

    def _chunk_text(self, text: str, source: str) -> list[dict]:
        """Split text into overlapping chunks with metadata."""
        chunks: list[dict] = []
        size = config.chunk_size
        overlap = config.chunk_overlap
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunk_text = text[start:end]
            chunk_id = hashlib.sha256(
                f"{source}:{idx}:{chunk_text[:64]}".encode()
            ).hexdigest()[:16]
            chunks.append(
                {
                    "id": f"{source}_{chunk_id}",
                    "text": chunk_text,
                    "metadata": {
                        "source": source,
                        "chunk_index": idx,
                        "char_start": start,
                        "char_end": end,
                    },
                }
            )
            start += size - overlap
            idx += 1
        return chunks

    # -- Indexing --------------------------------------------------------------

    async def index_file(self, file_path: str) -> int:
        """Read, chunk, embed, and store a single file. Returns chunk count."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            return 0

        chunks = self._chunk_text(text, path.name)
        if not chunks:
            return 0

        model = self._get_model()
        texts = [c["text"] for c in chunks]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection = self._get_collection()
        collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=texts,
            metadatas=[c["metadata"] for c in chunks],
            embeddings=embeddings,
        )
        logger.info("Indexed %d chunks from %s", len(chunks), path.name)
        return len(chunks)

    async def index_folder(self, folder_path: str) -> dict:
        """Index all supported files in a folder. Returns summary dict."""
        supported_ext = {".txt", ".md", ".pdf", ".csv", ".json", ".log"}
        folder = Path(folder_path)
        if not folder.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder_path}")

        files = [
            f for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in supported_ext
        ]
        total_chunks = 0
        processed = 0
        failed = 0
        errors: list[str] = []

        for f in files:
            try:
                n = await self.index_file(str(f))
                total_chunks += n
                processed += 1
            except Exception as exc:
                failed += 1
                errors.append(f"{f.name}: {exc}")
                logger.warning("Failed to index %s: %s", f.name, exc)

        return {
            "total_files": len(files),
            "processed": processed,
            "failed": failed,
            "total_chunks": total_chunks,
            "errors": errors[:20],  # cap error list
        }

    # -- Retrieval -------------------------------------------------------------

    async def query(self, query_text: str, top_k: int | None = None) -> list[dict]:
        """Embed query and retrieve top-k similar chunks."""
        k = top_k or config.default_top_k
        model = self._get_model()
        embedding = model.encode([query_text], show_progress_bar=False).tolist()[0]

        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                hits.append(
                    {
                        "id": doc_id,
                        "text": results["documents"][0][i] if results["documents"] else "",
                        "source": (
                            results["metadatas"][0][i].get("source", "unknown")
                            if results["metadatas"]
                            else "unknown"
                        ),
                        "chunk_index": (
                            results["metadatas"][0][i].get("chunk_index", 0)
                            if results["metadatas"]
                            else 0
                        ),
                        "similarity": round(
                            1 - (results["distances"][0][i] if results["distances"] else 0),
                            4,
                        ),
                    }
                )
        return hits

    async def search_similar(self, query_text: str, top_k: int | None = None) -> list[dict]:
        """Alias for query - returns raw similarity results."""
        return await self.query(query_text, top_k)

    # -- Document management ---------------------------------------------------

    async def get_document_summary(self, source: str) -> dict:
        """Get metadata summary for a given source document."""
        collection = self._get_collection()
        results = collection.get(
            where={"source": source},
            include=["metadatas", "documents"],
        )
        if not results or not results["ids"]:
            return {"source": source, "found": False, "chunks": 0}

        chunks = results["documents"] or []
        preview = chunks[0][:500] if chunks else ""
        return {
            "source": source,
            "found": True,
            "chunks": len(results["ids"]),
            "preview": preview,
        }

    async def list_documents(self) -> list[str]:
        """List all unique source document names in the collection."""
        collection = self._get_collection()
        all_data = collection.get(include=["metadatas"])
        sources: set[str] = set()
        if all_data and all_data["metadatas"]:
            for meta in all_data["metadatas"]:
                src = meta.get("source")
                if src:
                    sources.add(src)
        return sorted(sources)

    async def delete_document(self, source: str) -> int:
        """Delete all chunks belonging to a source document. Returns count deleted."""
        collection = self._get_collection()
        existing = collection.get(where={"source": source})
        if not existing or not existing["ids"]:
            return 0
        ids_to_delete = existing["ids"]
        collection.delete(ids=ids_to_delete)
        logger.info("Deleted %d chunks for source '%s'", len(ids_to_delete), source)
        return len(ids_to_delete)

    async def reset(self) -> int:
        """Delete the entire collection and recreate it. Returns previous document count."""
        collection = self._get_collection()
        count = collection.count()
        client = self._get_client()
        client.delete_collection(config.chroma_collection)
        self._collection = None  # force re-creation on next access
        logger.info("Reset collection '%s' (%d chunks removed)", config.chroma_collection, count)
        return count

    async def status(self) -> dict:
        """Return current status of the vector store."""
        try:
            collection = self._get_collection()
            count = collection.count()
            return {
                "status": "connected",
                "collection": config.chroma_collection,
                "total_chunks": count,
                "embedding_model": config.embedding_model,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }
