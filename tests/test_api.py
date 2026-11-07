"""Unit tests for FastAPI admin backend routes, authentication, and validation."""

import base64

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db import get_db
from app.main import app


def make_auth_headers(username: str = None, password: str = None) -> dict[str, str]:
    u = username or settings.DASHBOARD_USERNAME
    p = password or settings.DASHBOARD_PASSWORD
    token = base64.b64encode(f"{u}:{p}".encode()).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


@pytest.mark.asyncio
async def test_auth_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # No credentials
        r1 = await client.get("/api/login")
        assert r1.status_code == 401

        # Wrong password
        wrong_headers = make_auth_headers(password="wrong-password")
        r2 = await client.get("/api/login", headers=wrong_headers)
        assert r2.status_code == 401


@pytest.mark.asyncio
async def test_auth_success():
    transport = ASGITransport(app=app)
    auth_headers = make_auth_headers()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/login", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "authenticated"


@pytest.mark.asyncio
async def test_api_tickets_and_messages_endpoints():
    transport = ASGITransport(app=app)
    auth_headers = make_auth_headers()
    db = get_db()

    # Seed a ticket
    ticket_id = db.upsert_ticket(
        thread_id="th-api-1",
        customer="test@example.com",
        subject="Paddle inquiry",
        category="paddle-boards",
        status="open",
    )
    db.save_message(
        ticket_id=ticket_id,
        message_id="msg-api-1",
        direction="incoming",
        sender="test@example.com",
        recipient="support@example.com",
        body="How much is the 11' board?",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List tickets
        res_list = await client.get("/api/tickets", headers=auth_headers)
        assert res_list.status_code == 200
        tickets = res_list.json()
        assert len(tickets) >= 1

        # Get ticket details
        res_detail = await client.get(f"/api/tickets/{ticket_id}", headers=auth_headers)
        assert res_detail.status_code == 200
        assert res_detail.json()["thread_id"] == "th-api-1"

        # Get ticket messages
        res_msgs = await client.get(
            f"/api/tickets/{ticket_id}/messages", headers=auth_headers
        )
        assert res_msgs.status_code == 200
        msgs = res_msgs.json()
        assert len(msgs) == 1
        assert msgs[0]["body"] == "How much is the 11' board?"

        # Nonexistent ticket
        res_404 = await client.get("/api/tickets/nonexistent-id", headers=auth_headers)
        assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_api_knowledge_base_endpoints():
    transport = ASGITransport(app=app)
    auth_headers = make_auth_headers()
    db = get_db()

    entry_id = db.upsert_kb_entry(
        section="shipping",
        title="Delivery Areas",
        content="We ship to all 50 states.",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List KB
        res = await client.get("/api/knowledge-base", headers=auth_headers)
        assert res.status_code == 200
        entries = res.json()
        assert any(e["id"] == entry_id for e in entries)

        # Update KB
        update_payload = {
            "title": "Delivery Areas",
            "content": "Updated shipping areas text.",
        }
        res_update = await client.put(
            f"/api/knowledge-base/{entry_id}", json=update_payload, headers=auth_headers
        )
        assert res_update.status_code == 200
        assert res_update.json()["entry"]["content"] == "Updated shipping areas text."


@pytest.mark.asyncio
async def test_api_manual_poll_endpoint():
    transport = ASGITransport(app=app)
    auth_headers = make_auth_headers()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/poll", headers=auth_headers)
        assert res.status_code == 200
        assert "processed" in res.json()


@pytest.mark.asyncio
async def test_api_update_ticket_status_and_assignment():
    transport = ASGITransport(app=app)
    auth_headers = make_auth_headers()
    db = get_db()

    ticket_id = db.upsert_ticket(
        thread_id="th-patch-1",
        customer="patch@example.com",
        subject="Status update test",
        category="general",
        status="open",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        patch_res = await client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "resolved", "assigned_to": "alice"},
            headers=auth_headers,
        )
        assert patch_res.status_code == 200
        data = patch_res.json()["ticket"]
        assert data["status"] == "resolved"
        assert data["assigned_to"] == "alice"


@pytest.mark.asyncio
async def test_api_manual_ticket_reply():
    transport = ASGITransport(app=app)
    auth_headers = make_auth_headers()
    db = get_db()

    ticket_id = db.upsert_ticket(
        thread_id="th-reply-manual-1",
        customer="manual@example.com",
        subject="Manual reply test",
        category="shelving",
        status="escalated",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reply_res = await client.post(
            f"/api/tickets/{ticket_id}/reply",
            json={"body": "We have expedited a replacement hardware pack."},
            headers=auth_headers,
        )
        assert reply_res.status_code == 200
        assert reply_res.json()["status"] == "sent"

        # Check messages
        msgs = db.get_ticket_messages(ticket_id)
        assert len(msgs) == 1
        assert msgs[0]["direction"] == "outgoing"
        assert "expedited" in msgs[0]["body"]

        # Check ticket status updated to answered
        updated = db.get_ticket(ticket_id)
        assert updated["status"] == "answered"


@pytest.mark.asyncio
async def test_api_ticket_notes():
    transport = ASGITransport(app=app)
    auth_headers = make_auth_headers()
    db = get_db()

    ticket_id = db.upsert_ticket(
        thread_id="th-notes-1",
        customer="notes@example.com",
        subject="Notes test",
        category="general",
        status="open",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Add note
        post_res = await client.post(
            f"/api/tickets/{ticket_id}/notes",
            json={"note": "VIP account holder, handle with priority"},
            headers=auth_headers,
        )
        assert post_res.status_code == 200
        assert post_res.json()["status"] == "created"

        # List notes
        get_res = await client.get(
            f"/api/tickets/{ticket_id}/notes",
            headers=auth_headers,
        )
        assert get_res.status_code == 200
        notes = get_res.json()
        assert len(notes) == 1
        assert notes[0]["note"] == "VIP account holder, handle with priority"
        assert notes[0]["author"] == "admin"
