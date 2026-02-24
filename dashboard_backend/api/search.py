"""Search endpoint that queries ChromaDB directly for RAG results."""

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard_backend.config import get_settings
from dashboard_backend.db import get_db
from dashboard_backend.models import QueryLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard/search", tags=["search"])


class SearchResult(BaseModel):
    id: str
    text: str
    source: str
    chunk_index: int
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    result_count: int
    response_time_ms: int


@router.get("", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query text"),
    top_k: int = Query(default=5, ge=1, le=20, description="Number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Search indexed documents using ChromaDB vector similarity."""
    settings = get_settings()
    start = time.time()

    try:
        import chromadb

        client = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port
        )
        collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

        # ChromaDB's default embedding function handles embedding the query
        results = collection.query(
            query_texts=[q],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[SearchResult] = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                hits.append(
                    SearchResult(
                        id=doc_id,
                        text=results["documents"][0][i] if results["documents"] else "",
                        source=(
                            results["metadatas"][0][i].get("source", "unknown")
                            if results["metadatas"]
                            else "unknown"
                        ),
                        chunk_index=(
                            results["metadatas"][0][i].get("chunk_index", 0)
                            if results["metadatas"]
                            else 0
                        ),
                        similarity=round(
                            1 - (results["distances"][0][i] if results["distances"] else 0),
                            4,
                        ),
                    )
                )

        elapsed_ms = int((time.time() - start) * 1000)

        # Log the query to the database
        try:
            sources_json = [
                {"source": h.source, "chunk_index": h.chunk_index, "similarity": h.similarity}
                for h in hits
            ]
            response_text = (
                f"Found {len(hits)} results" if hits else "No results found"
            )
            query_log = QueryLog(
                id=uuid.uuid4(),
                query_text=q,
                response_text=response_text,
                sources=sources_json,
                response_time_ms=elapsed_ms,
                timestamp=datetime.now(timezone.utc),
                client_type="dashboard",
                session_id="dashboard",
            )
            db.add(query_log)
            await db.commit()
        except Exception as log_exc:
            logger.debug("Failed to log query: %s", log_exc)

        return SearchResponse(
            query=q,
            results=hits,
            result_count=len(hits),
            response_time_ms=elapsed_ms,
        )

    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.error("Search failed: %s", exc)
        return SearchResponse(
            query=q,
            results=[],
            result_count=0,
            response_time_ms=elapsed_ms,
        )
