"""Main MCP server exposing RAG tools and stats resources."""

import asyncio
import json
import logging
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from .config import config
from .logging_utils import (
    QueryTimer,
    create_indexing_job,
    get_job_stats,
    get_query_stats,
    get_system_stats,
    log_query,
    update_indexing_job,
)
from .models import init_db
from .rag_engine import RAGEngine

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

app = Server(config.server_name)
rag = RAGEngine()

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="index_documents",
        description="Index all supported documents in a folder into the vector store. Logs the indexing job to the database.",
        inputSchema={
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "Path to the folder containing documents to index.",
                },
            },
            "required": ["folder_path"],
        },
    ),
    Tool(
        name="query_documents",
        description="Run a RAG query against indexed documents. Returns relevant passages with sources.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="search_similar",
        description="Search for documents similar to the query. Returns a list of matching chunks with similarity scores.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_document_summary",
        description="Get a summary of a specific indexed document including chunk count and preview.",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "The document source name (filename).",
                },
            },
            "required": ["source"],
        },
    ),
    Tool(
        name="list_indexed_documents",
        description="List all unique document sources currently in the vector store.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="delete_document",
        description="Delete all indexed chunks for a specific document.",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "The document source name to delete.",
                },
            },
            "required": ["source"],
        },
    ),
    Tool(
        name="reset_index",
        description="Delete the entire vector index and start fresh. This is irreversible.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="check_status",
        description="Check the current status of the RAG system including vector store connectivity and counts.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool calls to the appropriate handler."""
    try:
        result = await _dispatch_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as exc:
        logger.exception("Tool '%s' failed", name)
        error_body = {"error": str(exc), "tool": name}
        return [TextContent(type="text", text=json.dumps(error_body, indent=2))]


async def _dispatch_tool(name: str, arguments: dict) -> dict:
    if name == "index_documents":
        return await _tool_index_documents(arguments)
    elif name == "query_documents":
        return await _tool_query_documents(arguments)
    elif name == "search_similar":
        return await _tool_search_similar(arguments)
    elif name == "get_document_summary":
        return await _tool_get_document_summary(arguments)
    elif name == "list_indexed_documents":
        return await _tool_list_indexed_documents()
    elif name == "delete_document":
        return await _tool_delete_document(arguments)
    elif name == "reset_index":
        return await _tool_reset_index()
    elif name == "check_status":
        return await _tool_check_status()
    else:
        return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def _tool_index_documents(args: dict) -> dict:
    folder_path = args["folder_path"]

    # Create job in database
    job_id = await create_indexing_job(
        source_type="local",
        source_url=folder_path,
    )
    await update_indexing_job(job_id, status="processing")

    try:
        result = await rag.index_folder(folder_path)
        await update_indexing_job(
            job_id,
            status="completed",
            processed_files=result["processed"],
            failed_files=result["failed"],
            total_files=result["total_files"],
            progress_percent=100,
        )
        result["job_id"] = str(job_id)
        return result
    except Exception as exc:
        await update_indexing_job(
            job_id,
            status="failed",
            error_message=str(exc),
        )
        raise


async def _tool_query_documents(args: dict) -> dict:
    query_text = args["query"]
    top_k = args.get("top_k", config.default_top_k)

    with QueryTimer() as timer:
        hits = await rag.query(query_text, top_k)

    sources = [
        {"source": h["source"], "chunk_index": h["chunk_index"], "similarity": h["similarity"]}
        for h in hits
    ]

    # Build response text from retrieved chunks
    if hits:
        passages = "\n\n---\n\n".join(
            f"[{h['source']} chunk {h['chunk_index']}] (similarity: {h['similarity']})\n{h['text']}"
            for h in hits
        )
        response_text = f"Found {len(hits)} relevant passages:\n\n{passages}"
    else:
        response_text = "No relevant documents found for this query."

    await log_query(
        query_text=query_text,
        response_text=response_text,
        sources=sources,
        response_time_ms=timer.elapsed_ms,
    )

    return {
        "query": query_text,
        "response": response_text,
        "sources": sources,
        "response_time_ms": timer.elapsed_ms,
        "result_count": len(hits),
    }


async def _tool_search_similar(args: dict) -> dict:
    query_text = args["query"]
    top_k = args.get("top_k", config.default_top_k)

    with QueryTimer() as timer:
        hits = await rag.search_similar(query_text, top_k)

    sources = [
        {"source": h["source"], "chunk_index": h["chunk_index"], "similarity": h["similarity"]}
        for h in hits
    ]

    await log_query(
        query_text=query_text,
        response_text=f"search_similar returned {len(hits)} results",
        sources=sources,
        response_time_ms=timer.elapsed_ms,
    )

    return {
        "query": query_text,
        "results": hits,
        "response_time_ms": timer.elapsed_ms,
    }


async def _tool_get_document_summary(args: dict) -> dict:
    source = args["source"]
    return await rag.get_document_summary(source)


async def _tool_list_indexed_documents() -> dict:
    docs = await rag.list_documents()
    return {"documents": docs, "count": len(docs)}


async def _tool_delete_document(args: dict) -> dict:
    source = args["source"]
    deleted = await rag.delete_document(source)
    return {"source": source, "chunks_deleted": deleted}


async def _tool_reset_index() -> dict:
    previous = await rag.reset()
    return {"message": "Index has been reset.", "chunks_removed": previous}


async def _tool_check_status() -> dict:
    rag_status = await rag.status()
    system = await get_system_stats()
    return {"rag": rag_status, "system": system}


# ---------------------------------------------------------------------------
# Resource definitions
# ---------------------------------------------------------------------------

RESOURCES = [
    Resource(uri="stats://queries", name="Query Statistics", description="Aggregated query log statistics"),
    Resource(uri="stats://documents", name="Document Statistics", description="Indexed document statistics"),
    Resource(uri="stats://jobs", name="Job Statistics", description="Indexing job statistics"),
    Resource(uri="stats://system", name="System Health", description="Live system health metrics"),
]


@app.list_resources()
async def list_resources() -> list[Resource]:
    return RESOURCES


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Return JSON stats for the requested resource URI."""
    uri_str = str(uri)
    if uri_str == "stats://queries":
        data = await get_query_stats()
    elif uri_str == "stats://documents":
        docs = await rag.list_documents()
        rag_status = await rag.status()
        data = {
            "documents": docs,
            "count": len(docs),
            "total_chunks": rag_status.get("total_chunks", 0),
        }
    elif uri_str == "stats://jobs":
        data = await get_job_stats()
    elif uri_str == "stats://system":
        data = await get_system_stats()
    else:
        data = {"error": f"Unknown resource: {uri_str}"}
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main():
    """Run the MCP server over stdio."""
    logger.info("Initialising database tables...")
    await init_db()
    logger.info("Starting MCP server '%s'...", config.server_name)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run():
    """Synchronous entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
