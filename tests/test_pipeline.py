"""Integration tests for safe email processing pipeline, poller, and guards."""

import pytest

from app.db import SQLiteMemoryDatabase
from app.gmail import (
    LABEL_AI_PROCESSED,
    LABEL_NEEDS_HUMAN,
    MockGmailClient,
    ParsedEmail,
)
from app.pipeline import process_email_message
from app.poller import poll_once


@pytest.fixture
def mock_env():
    client = MockGmailClient(support_email="support@harborandpine.example.com")
    db = SQLiteMemoryDatabase(":memory:")
    return client, db


@pytest.mark.asyncio
async def test_normal_reply_pipeline(mock_env):
    client, db = mock_env
    email = ParsedEmail(
        message_id="msg-1",
        thread_id="th-1",
        sender="Tom <tom@example.com>",
        recipient="support@harborandpine.example.com",
        subject="Which board for 90kg?",
        body="Hi, I weigh 90 kg. Which paddle board should I buy?",
        date="Fri, 31 Oct 2026",
    )
    client.add_mock_message(email)

    res = await process_email_message("msg-1", "th-1", gmail_client=client, db=db)
    assert res["status"] == "completed"
    assert res["action"] == "reply"

    # Verify database state
    ticket = db.get_ticket(res["ticket_id"])
    assert ticket["status"] == "answered"
    assert ticket["category"] == "paddle-boards"

    messages = db.get_ticket_messages(ticket["id"])
    assert len(messages) == 2  # incoming and outgoing
    assert messages[0]["direction"] == "incoming"
    assert messages[1]["direction"] == "outgoing"

    # Verify Gmail state
    assert LABEL_AI_PROCESSED in client.labels["msg-1"]
    assert len(client.sent_messages) == 1
    assert "11' All-round" in client.sent_messages[0]["body"]


@pytest.mark.asyncio
async def test_escalation_pipeline(mock_env):
    client, db = mock_env
    email = ParsedEmail(
        message_id="msg-2",
        thread_id="th-2",
        sender="Sam <sam@example.com>",
        recipient="support@harborandpine.example.com",
        subject="No pump in the box",
        body="My 11' board arrived without the pump. Order 112-4839201-5528341.",
        date="Fri, 31 Oct 2026",
    )
    client.add_mock_message(email)

    res = await process_email_message("msg-2", "th-2", gmail_client=client, db=db)
    assert res["status"] == "completed"
    assert res["action"] == "escalate"

    ticket = db.get_ticket(res["ticket_id"])
    assert ticket["status"] == "escalated"
    assert ticket["proposed_action"] == "ship-part"
    assert LABEL_NEEDS_HUMAN in client.labels["msg-2"]


@pytest.mark.asyncio
async def test_human_owned_thread_protection(mock_env):
    client, db = mock_env
    thread_id = "th-human"

    # Pre-populate escalated ticket owned by human
    db.upsert_ticket(
        thread_id=thread_id,
        customer="vip@example.com",
        subject="Urgent review",
        category="escalation-rules",
        status="escalated",
    )

    followup_email = ParsedEmail(
        message_id="msg-followup",
        thread_id=thread_id,
        sender="vip@example.com",
        recipient="support@harborandpine.example.com",
        subject="Re: Urgent review",
        body="Any update on my issue?",
        date="Fri, 31 Oct 2026",
    )
    client.add_mock_message(followup_email)

    res = await process_email_message(
        "msg-followup", thread_id, gmail_client=client, db=db
    )
    assert res["status"] == "completed"
    assert res["action"] == "escalate"

    # Confirm no automated reply was sent
    assert len(client.sent_messages) == 0


@pytest.mark.asyncio
async def test_self_sent_message_skipped(mock_env):
    client, db = mock_env
    own_email = ParsedEmail(
        message_id="msg-own",
        thread_id="th-own",
        sender="support@harborandpine.example.com",
        recipient="customer@example.com",
        subject="Our previous reply",
        body="Here is information.",
        date="Fri, 31 Oct 2026",
    )
    client.add_mock_message(own_email)

    res = await process_email_message("msg-own", "th-own", gmail_client=client, db=db)
    assert res["status"] == "skipped"
    assert "support mailbox itself" in res["reason"]
    assert len(client.sent_messages) == 0


@pytest.mark.asyncio
async def test_duplicate_poll_prevention(mock_env):
    client, db = mock_env
    email = ParsedEmail(
        message_id="msg-dup",
        thread_id="th-dup",
        sender="alice@example.com",
        recipient="support@harborandpine.example.com",
        subject="Shelving dimensions",
        body="Which side does the back panel face?",
        date="Fri, 31 Oct 2026",
    )
    client.add_mock_message(email)

    # First poll cycle processes the message
    count1 = await poll_once(gmail_client=client, db=db)
    assert count1 == 1
    assert len(client.sent_messages) == 1

    # Second poll cycle finds 0 unprocessed messages because label was applied
    count2 = await poll_once(gmail_client=client, db=db)
    assert count2 == 0
    # Sent messages count remains strictly 1 (no duplicate replies)
    assert len(client.sent_messages) == 1
