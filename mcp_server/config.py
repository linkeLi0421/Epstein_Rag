"""Configuration management for the MCP RAG Server."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Server configuration loaded from environment variables."""

    # Database
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/epstein_rag",
        )
    )

    # ChromaDB
    chroma_host: str = field(
        default_factory=lambda: os.getenv("CHROMA_HOST", "localhost")
    )
    chroma_port: int = field(
        default_factory=lambda: int(os.getenv("CHROMA_PORT", "8000"))
    )
    chroma_collection: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION", "epstein_documents")
    )

    # Embedding model
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
    )

    # RAG settings
    chunk_size: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000"))
    )
    chunk_overlap: int = field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "200"))
    )
    default_top_k: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_TOP_K", "5"))
    )

    # Server
    server_name: str = field(
        default_factory=lambda: os.getenv("MCP_SERVER_NAME", "epstein-rag")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )


config = Config()
