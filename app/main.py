"""FastAPI Application entrypoint for ResolveHelm Admin API and dashboard backend."""

import logging
import os
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.db import get_db

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("resolvehelm")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    logger.info("Starting ResolveHelm API in %s mode", settings.APP_ENV)
    yield
    logger.info("Shutting down ResolveHelm API")


app = FastAPI(
    title="ResolveHelm API",
    description="Policy-Aware AI Customer Support Automation Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware supporting local development, Vercel deployments, and GitHub Pages
cors_origins_raw = getattr(settings, "CORS_ALLOWED_ORIGINS", "*").strip()
if cors_origins_raw == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    allowed_list = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_list,
        allow_origin_regex=r"^https://.*\.github\.io$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Validate HTTP Basic authentication against configured dashboard credentials."""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), settings.DASHBOARD_USERNAME.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), settings.DASHBOARD_PASSWORD.encode("utf8")
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: Exception) -> JSONResponse:
    """Diagnostic 404 handler to reveal path routing in serverless runtimes."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Not Found",
            "path": request.url.path,
            "scope_path": request.scope.get("path"),
            "scope_root_path": request.scope.get("root_path"),
            "query_params": dict(request.query_params),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safe global exception handler avoiding internal leak in production."""
    logger.exception(
        "Unhandled error on %s %s: %s", request.method, request.url.path, exc
    )
    if settings.APP_ENV == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


# ------------------------------------------------------------------------------
# System & Health Routes (Public)
# ------------------------------------------------------------------------------


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Liveness probe returning application state and configuration summary."""
    return {
        "status": "healthy",
        "app": "ResolveHelm",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
        "dry_run": settings.DRY_RUN,
        "auto_send_enabled": settings.AUTO_SEND_ENABLED,
    }


@app.get("/health/ready", tags=["System"])
async def readiness_check() -> dict[str, Any]:
    """Dependency-aware readiness probe for load balancers and orchestrators."""
    checks = {
        "config": True,
        "database": False,
        "gmail": False,
    }

    try:
        from app.db import check_db_health

        checks["database"] = await check_db_health()
    except (ImportError, ConnectionError, OSError) as e:
        logger.debug("Database readiness check failed: %s", e)
        checks["database"] = False

    checks["gmail"] = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_REFRESH_TOKEN)

    return {
        "ready": checks["config"],
        "checks": checks,
    }


# ------------------------------------------------------------------------------
# Authenticated Admin Dashboard Routes
# ------------------------------------------------------------------------------


@app.get("/api/login", tags=["Auth"])
async def login_check(username: str = Depends(require_auth)) -> dict[str, Any]:
    """Verify administrator authentication."""
    return {"status": "authenticated", "user": username}


@app.get("/api/events", tags=["Events"])
async def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Retrieve recent processing lifecycle events with pagination."""
    db = get_db()
    return db.list_recent_events(limit=limit, offset=offset)


@app.get("/api/tickets", tags=["Tickets"])
async def list_tickets(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Retrieve support tickets with pagination."""
    db = get_db()
    return db.list_tickets(limit=limit, offset=offset)


@app.get("/api/tickets/{ticket_id}", tags=["Tickets"])
async def get_ticket_details(
    ticket_id: str,
    _: str = Depends(require_auth),
) -> dict[str, Any]:
    """Retrieve ticket record by ID."""
    db = get_db()
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    return ticket


@app.get("/api/tickets/{ticket_id}/messages", tags=["Tickets"])
async def get_ticket_messages(
    ticket_id: str,
    _: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Retrieve conversation messages for a ticket."""
    db = get_db()
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    return db.get_ticket_messages(ticket_id)


class TicketUpdateRequest(BaseModel):
    status: Literal["open", "answered", "escalated", "closed", "resolved"] | None = None
    assigned_to: str | None = None


@app.patch("/api/tickets/{ticket_id}", tags=["Tickets"])
async def update_ticket_endpoint(
    ticket_id: str,
    payload: TicketUpdateRequest,
    _: str = Depends(require_auth),
) -> dict[str, Any]:
    """Update ticket status and operator assignment."""
    db = get_db()
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    success = db.update_ticket(
        ticket_id=ticket_id,
        status=payload.status,
        assigned_to=payload.assigned_to,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket",
        )
    updated = db.get_ticket(ticket_id)
    return {"status": "updated", "ticket": updated}


class TicketManualReplyRequest(BaseModel):
    body: str = Field(min_length=1, max_length=50000)


@app.post("/api/tickets/{ticket_id}/reply", tags=["Tickets"])
async def send_manual_ticket_reply(
    ticket_id: str,
    payload: TicketManualReplyRequest,
    user: str = Depends(require_auth),
) -> dict[str, Any]:
    """Send an operator manual response to the customer thread."""
    db = get_db()
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )

    msg_id = f"manual-{secrets.token_hex(8)}"
    db.save_message(
        ticket_id=ticket_id,
        message_id=msg_id,
        direction="outgoing",
        sender=f"support ({user})",
        recipient=ticket["customer"],
        body=payload.body,
    )
    db.update_ticket(ticket_id=ticket_id, status="answered")
    return {"status": "sent", "message_id": msg_id}


class TicketNoteCreateRequest(BaseModel):
    note: str = Field(min_length=1, max_length=10000)


@app.get("/api/tickets/{ticket_id}/notes", tags=["Tickets"])
async def get_ticket_notes_endpoint(
    ticket_id: str,
    _: str = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Retrieve internal operator notes for a ticket."""
    db = get_db()
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    return db.get_ticket_notes(ticket_id)


@app.post("/api/tickets/{ticket_id}/notes", tags=["Tickets"])
async def add_ticket_note_endpoint(
    ticket_id: str,
    payload: TicketNoteCreateRequest,
    user: str = Depends(require_auth),
) -> dict[str, Any]:
    """Record an internal support note on a ticket."""
    db = get_db()
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    note_id = db.add_ticket_note(
        ticket_id=ticket_id,
        note=payload.note,
        author=user,
    )
    return {"status": "created", "note_id": note_id}


@app.get("/api/knowledge-base", tags=["Knowledge Base"])
async def list_knowledge_base(_: str = Depends(require_auth)) -> list[dict[str, Any]]:
    """Retrieve all policy entries across all knowledge base sections."""
    db = get_db()
    return db.get_all_kb_entries()


class KnowledgeBaseUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=50000)


@app.put("/api/knowledge-base/{entry_id}", tags=["Knowledge Base"])
async def update_knowledge_base_entry(
    entry_id: str,
    payload: KnowledgeBaseUpdateRequest,
    _: str = Depends(require_auth),
) -> dict[str, Any]:
    """Update title and content of a knowledge base entry."""
    db = get_db()
    existing = db.get_kb_entry_by_id(entry_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found",
        )

    success = db.update_kb_entry(
        entry_id=entry_id, title=payload.title, content=payload.content
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entry",
        )

    updated = db.get_kb_entry_by_id(entry_id)
    return {"status": "updated", "entry": updated}


@app.post("/api/poll", tags=["Poller"])
async def trigger_manual_poll(_: str = Depends(require_auth)) -> dict[str, Any]:
    """Trigger an immediate inbox poll cycle from the admin dashboard."""
    from app.poller import poll_once

    count = await poll_once()
    return {"status": "ok", "processed": count}


# ------------------------------------------------------------------------------
# Serve Production Dashboard Assets or Root API Info
# ------------------------------------------------------------------------------
dashboard_dist = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
if dashboard_dist.exists() and not bool(os.environ.get("VERCEL")):
    app.mount(
        "/", StaticFiles(directory=str(dashboard_dist), html=True), name="dashboard"
    )
else:

    @app.get("/", tags=["System"])
    async def root_discovery() -> dict[str, Any]:
        """Root discovery endpoint for serverless and headless deployments."""
        return {
            "service": "ResolveHelm API",
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.APP_ENV,
            "docs": "/docs",
            "health": "/health",
        }
