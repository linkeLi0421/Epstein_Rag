"""FastAPI application entry point for the Epstein RAG Dashboard Backend.

Serves as the observability API for the dashboard frontend, providing
read-only access to query logs, indexing jobs, system health, and analytics
from the shared PostgreSQL database used by the MCP server.

Run with:
    uvicorn dashboard_backend.main:app --host 0.0.0.0 --port 8001 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dashboard_backend.api import health, jobs, queries, websocket
from dashboard_backend.config import get_settings
from dashboard_backend.db import close_db, init_db

logger = logging.getLogger("dashboard_backend")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    # Startup
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting Dashboard Backend on port %s", settings.port)
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Dashboard Backend")
    await close_db()


app = FastAPI(
    title="Epstein RAG Dashboard API",
    description="Observability API for the Epstein RAG system. Provides query monitoring, job tracking, system health, and analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend at localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug("%s %s", request.method, request.url.path)
    response = await call_next(request)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Register routers
app.include_router(queries.router)
app.include_router(jobs.router)
app.include_router(health.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "service": "Epstein RAG Dashboard Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "queries": "/api/dashboard/queries",
            "query_stats": "/api/dashboard/queries/stats",
            "jobs": "/api/dashboard/jobs",
            "health": "/api/dashboard/health",
            "metrics": "/api/dashboard/metrics",
            "analytics": "/api/dashboard/analytics",
            "websocket": "/ws/dashboard",
        },
    }
