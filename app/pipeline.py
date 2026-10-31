"""End-to-end safe email processing pipeline linking Gmail, DB, rules, and AI."""

import logging
from typing import Any

from app.ai.decide import decide
from app.config import settings
from app.db import BaseDatabase, get_db
from app.gmail import (
    LABEL_AI_PROCESSED,
    LABEL_NEEDS_HUMAN,
    GmailClient,
    format_thread_for_ai,
)
from app.guards import should_skip_message

logger = logging.getLogger(__name__)


async def process_email_message(
    message_id: str,
    thread_id: str,
    gmail_client: Any | None = None,
    db: BaseDatabase | None = None,
) -> dict[str, Any]:
    """Execute the complete safe processing pipeline for a single incoming email message."""
    if gmail_client is None:
        gmail_client = GmailClient()
    if db is None:
        db = get_db()

    logger.info(
        "Starting processing pipeline for message %s (thread: %s)",
        message_id,
        thread_id,
    )

    # 1. Claim event atomically in database
    if not db.claim_event(message_id, max_attempts=settings.MAX_MESSAGE_ATTEMPTS):
        logger.info(
            "Message %s already claimed, processing, or exceeded max attempts; skipping",
            message_id,
        )
        return {"status": "skipped", "reason": "already_claimed_or_completed"}

    try:
        # 2. Fetch and parse incoming message
        email = gmail_client.get_message(message_id)

        # 3. Evaluate pre-processing safety guards
        support_email = gmail_client.get_support_email()
        skip, skip_reason = should_skip_message(email, support_email=support_email)
        if skip:
            logger.info("Skipping message %s: %s", message_id, skip_reason)
            db.complete_event(
                message_id, result={"action": "skip", "reason": skip_reason}
            )
            gmail_client.apply_label(message_id, LABEL_AI_PROCESSED)
            return {"status": "skipped", "reason": skip_reason}

        # 4. Check existing ticket for human escalation ownership
        existing_ticket = db.get_ticket_by_thread(thread_id)
        if existing_ticket and existing_ticket.get("status") == "escalated":
            logger.info(
                "Thread %s is already human-owned and escalated; bypassing auto-reply",
                thread_id,
            )
            ticket_id = existing_ticket["id"]
            db.save_message(
                ticket_id=ticket_id,
                message_id=message_id,
                direction="incoming",
                sender=email.sender,
                recipient=email.recipient,
                body=email.body,
            )
            db.complete_event(
                message_id,
                result={"action": "escalate", "reason": "Thread already human-owned"},
            )
            gmail_client.apply_label(message_id, LABEL_NEEDS_HUMAN)
            return {
                "status": "completed",
                "action": "escalate",
                "reason": "thread_already_escalated",
                "ticket_id": ticket_id,
            }

        # 5. Upsert ticket and persist incoming message
        ticket_id = db.upsert_ticket(
            thread_id=thread_id,
            customer=email.sender,
            subject=email.subject,
            category="general",
            status="open",
        )
        db.save_message(
            ticket_id=ticket_id,
            message_id=message_id,
            direction="incoming",
            sender=email.sender,
            recipient=email.recipient,
            body=email.body,
        )

        # 6. Fetch full conversation thread to format context
        thread_messages = gmail_client.get_thread(thread_id)

        # 6. Format thread history for decision engine
        formatted_thread = format_thread_for_ai(
            thread_messages, support_email=support_email
        )

        # 7. Execute AI & deterministic rules decision
        decision = await decide(formatted_thread, has_attachments=email.has_attachments)
        logger.info(
            "Decision for msg %s: action=%s, section=%s, proposed_action=%s",
            message_id,
            decision.action,
            decision.section,
            decision.proposed_action,
        )

        # 8. Build reply MIME payload
        reply_mime = gmail_client.build_reply_mime(
            to_email=email.sender,
            subject=email.subject,
            body=decision.reply,
            rfc_message_id=email.rfc_message_id,
            thread_id=thread_id,
        )

        # 9. Send customer email (respects DRY_RUN)
        send_result = gmail_client.send_reply(reply_mime)
        out_msg_id = send_result.get("id", f"out-{message_id}")

        # 10. Persist outgoing message
        db.save_message(
            ticket_id=ticket_id,
            message_id=out_msg_id,
            direction="outgoing",
            sender=support_email or "support@harborandpine.example.com",
            recipient=email.sender,
            body=decision.reply,
        )

        # 11. Update ticket status and apply appropriate Gmail label
        final_ticket_status = "answered" if decision.action == "reply" else "escalated"
        target_label = (
            LABEL_AI_PROCESSED if decision.action == "reply" else LABEL_NEEDS_HUMAN
        )

        db.upsert_ticket(
            thread_id=thread_id,
            customer=email.sender,
            subject=email.subject,
            category=decision.section,
            status=final_ticket_status,
            proposed_action=decision.proposed_action,
        )

        gmail_client.apply_label(message_id, target_label)

        # 12. Finalize event record in database
        result_payload = {
            "action": decision.action,
            "section": decision.section,
            "proposed_action": decision.proposed_action,
            "reason": decision.reason,
            "outbound_id": out_msg_id,
        }
        db.complete_event(message_id, result=result_payload)

        return {
            "status": "completed",
            "action": decision.action,
            "ticket_id": ticket_id,
        }

    except Exception as e:
        logger.exception("Pipeline execution failed for message %s: %s", message_id, e)
        db.fail_event(message_id, error=str(e), retryable=True)
        raise
