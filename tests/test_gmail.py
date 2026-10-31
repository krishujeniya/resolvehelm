"""Unit tests for Gmail client, message parsing, label management, and thread formatting."""

import base64

from app.gmail import (
    LABEL_AI_PROCESSED,
    MockGmailClient,
    ParsedEmail,
    clean_quoted_history,
    format_thread_for_ai,
    is_automated_sender,
    parse_gmail_message,
)


def test_clean_quoted_history():
    body_with_quotes = (
        "Hello, I need help with my paddle board.\n\n"
        "On Oct 30, 2026, at 10:00 AM, Support <support@example.com> wrote:\n"
        "> Thank you for contacting us.\n"
        "> Have you checked the valve?"
    )
    cleaned = clean_quoted_history(body_with_quotes)
    assert cleaned == "Hello, I need help with my paddle board."


def test_is_automated_sender_detection():
    # Regular customer email
    assert not is_automated_sender({"From": "customer@example.com", "Subject": "Help"})

    # Auto-submitted header
    assert is_automated_sender(
        {"From": "user@example.com", "Auto-Submitted": "auto-replied"}
    )

    # Precedence bulk
    assert is_automated_sender({"From": "sales@shop.com", "Precedence": "bulk"})

    # List ID
    assert is_automated_sender(
        {"From": "digest@forum.com", "List-Id": "<digest.forum.com>"}
    )

    # Noreply address
    assert is_automated_sender({"From": "noreply@github.com"})


def test_parse_gmail_message_multipart():
    sample_text = (
        "Hi, my 11' paddle board arrived without a pump. Order 112-4839201-5528341."
    )
    b64_data = base64.urlsafe_b64encode(sample_text.encode("utf-8")).decode("ASCII")

    raw_message = {
        "id": "msg-12345",
        "threadId": "thread-abc",
        "snippet": sample_text,
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Sam Lee <sam@example.com>"},
                {"name": "To", "value": "support@harborandpine.example.com"},
                {"name": "Subject", "value": "No pump in the box"},
                {"name": "Date", "value": "Fri, 31 Oct 2026 12:00:00 +0000"},
                {"name": "Message-ID", "value": "<sample-rfc-id@example.com>"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": b64_data},
                }
            ],
        },
    }

    parsed = parse_gmail_message(raw_message)
    assert parsed.message_id == "msg-12345"
    assert parsed.thread_id == "thread-abc"
    assert "Sam Lee" in parsed.sender
    assert parsed.subject == "No pump in the box"
    assert parsed.body == sample_text
    assert parsed.rfc_message_id == "<sample-rfc-id@example.com>"
    assert not parsed.has_attachments
    assert not parsed.is_automated


def test_parse_gmail_message_with_attachment():
    raw_message = {
        "id": "msg-attach",
        "threadId": "thread-attach",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "From", "value": "customer@example.com"},
                {"name": "Subject", "value": "Cracked board picture"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(b"Here is the photo.").decode(
                            "ASCII"
                        )
                    },
                },
                {
                    "mimeType": "image/jpeg",
                    "filename": "crack.jpg",
                    "body": {"attachmentId": "att-1"},
                },
            ],
        },
    }

    parsed = parse_gmail_message(raw_message)
    assert parsed.has_attachments is True
    assert "crack.jpg" in parsed.attachment_names


def test_format_thread_for_ai():
    msg1 = ParsedEmail(
        message_id="1",
        thread_id="t1",
        sender="Mia Jansen <mia@example.com>",
        recipient="support@example.com",
        subject="Board loses air",
        body="My board is soft every morning.",
        date="Oct 30",
    )
    msg2 = ParsedEmail(
        message_id="2",
        thread_id="t1",
        sender="support@example.com",
        recipient="Mia Jansen <mia@example.com>",
        subject="Re: Board loses air",
        body="Have you performed a valve check?",
        date="Oct 30",
    )
    msg3 = ParsedEmail(
        message_id="3",
        thread_id="t1",
        sender="Mia Jansen <mia@example.com>",
        recipient="support@example.com",
        subject="Re: Board loses air",
        body="Yes, I tightened it and it still loses air.",
        date="Oct 31",
    )

    thread_str = format_thread_for_ai(
        [msg1, msg2, msg3], support_email="support@example.com"
    )
    assert "Subject: Board loses air" in thread_str
    assert (
        "Customer (Mia Jansen <mia@example.com>):\nMy board is soft every morning."
        in thread_str
    )
    assert (
        "Support (support@example.com):\nHave you performed a valve check?"
        in thread_str
    )
    assert (
        "Customer (Mia Jansen <mia@example.com>):\nYes, I tightened it and it still loses air."
        in thread_str
    )


def test_mock_gmail_client_lifecycle():
    client = MockGmailClient()
    email = ParsedEmail(
        message_id="m1",
        thread_id="th1",
        sender="alice@example.com",
        recipient="support@example.com",
        subject="Question about 10'6 board",
        body="Can a 90kg person ride the 10'6 board?",
        date="Fri, 31 Oct 2026",
    )

    client.add_mock_message(email)

    # Eligible message in inbox
    unprocessed = client.list_unprocessed_inbox_messages()
    assert len(unprocessed) == 1
    assert unprocessed[0]["id"] == "m1"

    # Apply ai-processed label
    client.apply_label("m1", LABEL_AI_PROCESSED)
    assert len(client.list_unprocessed_inbox_messages()) == 0

    # Sending reply
    reply_mime = client.build_reply_mime(
        to_email=email.sender,
        subject=email.subject,
        body="For 90 kg, we recommend the 11' board.",
        thread_id="th1",
    )
    send_res = client.send_reply(reply_mime)
    assert send_res["simulated"] is True
    assert len(client.sent_messages) == 1
