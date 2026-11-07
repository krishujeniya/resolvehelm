"""Unit tests for database layer and state transitions."""

import pytest

from app.db import SQLiteMemoryDatabase


@pytest.fixture
def db():
    return SQLiteMemoryDatabase()


def test_db_health(db):
    assert db.check_health() is True


def test_event_claim_lifecycle(db):
    msg_id = "msg-100"

    # First claim succeeds
    assert db.claim_event(msg_id) is True

    # Concurrent claim while processing is rejected
    assert db.claim_event(msg_id) is False

    # Fail the event with retryable=True
    db.fail_event(msg_id, error="Transient timeout", retryable=True)

    # Claim again succeeds (attempt 2)
    assert db.claim_event(msg_id) is True

    # Complete the event
    db.complete_event(msg_id, result={"action": "reply", "category": "paddle-boards"})

    # Claim after completion is rejected
    assert db.claim_event(msg_id) is False

    events = db.list_recent_events()
    assert len(events) == 1
    assert events[0]["status"] == "completed"
    assert events[0]["result"]["action"] == "reply"
    assert events[0]["attempts"] == 2


def test_event_max_attempts(db):
    msg_id = "msg-fail"
    max_attempts = 2

    # Attempt 1
    assert db.claim_event(msg_id, max_attempts=max_attempts) is True
    db.fail_event(msg_id, error="Error 1", retryable=True)

    # Attempt 2
    assert db.claim_event(msg_id, max_attempts=max_attempts) is True
    db.fail_event(msg_id, error="Error 2", retryable=True)

    # Attempt 3 exceeds max_attempts -> claim rejected
    assert db.claim_event(msg_id, max_attempts=max_attempts) is False


def test_ticket_and_messages_lifecycle(db):
    thread_id = "thread-xyz"
    ticket_id = db.upsert_ticket(
        thread_id=thread_id,
        customer="buyer@example.com",
        subject="Missing manual",
        category="shelving",
        status="open",
    )
    assert ticket_id is not None

    # Upsert with new status
    updated_id = db.upsert_ticket(
        thread_id=thread_id,
        customer="buyer@example.com",
        subject="Missing manual",
        category="shelving",
        status="answered",
        proposed_action="ship-part",
    )
    assert updated_id == ticket_id

    ticket = db.get_ticket(ticket_id)
    assert ticket["status"] == "answered"
    assert ticket["proposed_action"] == "ship-part"

    # Save messages
    msg1_id = db.save_message(
        ticket_id=ticket_id,
        message_id="gmail-in-1",
        direction="incoming",
        sender="buyer@example.com",
        recipient="support@example.com",
        body="Where is the assembly manual?",
    )
    msg2_id = db.save_message(
        ticket_id=ticket_id,
        message_id="gmail-out-1",
        direction="outgoing",
        sender="support@example.com",
        recipient="buyer@example.com",
        body="Here is the PDF manual.",
    )
    assert msg1_id != msg2_id

    messages = db.get_ticket_messages(ticket_id)
    assert len(messages) == 2
    assert messages[0]["direction"] == "incoming"
    assert messages[1]["direction"] == "outgoing"


def test_knowledge_base_operations(db):
    entry1_id = db.upsert_kb_entry(
        section="paddle-boards",
        title="Sizes",
        content="10'6 is for riders up to 85 kg.",
    )
    db.upsert_kb_entry(
        section="paddle-boards",
        title="Valves",
        content="Tighten with valve wrench.",
    )
    db.upsert_kb_entry(
        section="shelving",
        title="Models",
        content="HP-S3 is 106 cm high.",
    )

    sections = db.list_kb_sections()
    assert sections == ["paddle-boards", "shelving"]

    pb_entries = db.get_kb_entries("paddle-boards")
    assert len(pb_entries) == 2

    # Update entry
    assert (
        db.update_kb_entry(entry1_id, title="Sizes", content="Updated sizing guide")
        is True
    )
    updated = db.get_kb_entry_by_id(entry1_id)
    assert updated["content"] == "Updated sizing guide"


def test_ticket_status_update_and_notes(db):
    ticket_id = db.upsert_ticket(
        thread_id="th-db-ops",
        customer="ops@example.com",
        subject="Notes and status test",
        category="paddle-boards",
        status="open",
    )

    # Update status to resolved and assign
    success = db.update_ticket(ticket_id, status="resolved", assigned_to="operator_bob")
    assert success is True

    ticket = db.get_ticket(ticket_id)
    assert ticket["status"] == "resolved"
    assert ticket["assigned_to"] == "operator_bob"

    # Add notes
    note1_id = db.add_ticket_note(
        ticket_id, note="Customer confirmed replacement received", author="bob"
    )
    assert note1_id is not None
    note2_id = db.add_ticket_note(
        ticket_id, note="Closing ticket after confirmation", author="bob"
    )
    assert note2_id != note1_id

    notes = db.get_ticket_notes(ticket_id)
    assert len(notes) == 2
    assert notes[0]["author"] == "bob"
