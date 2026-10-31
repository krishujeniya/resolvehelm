"""Master decision orchestrator enforcing deterministic business rules and safety policies."""

import logging
import re

from app.ai.agent import generate_agent_reply
from app.ai.classifier import classify_email
from app.ai.rules import (
    check_mandatory_escalation,
    evaluate_general_rules,
    evaluate_paddle_board_rules,
    evaluate_shelving_rules,
)
from app.ai.schemas import Decision

logger = logging.getLogger(__name__)


def extract_subject_from_thread(email_text: str) -> str:
    """Extract Subject line if present in formatted thread."""
    match = re.search(r"^Subject:\s*(.+)$", email_text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def extract_sender_name(email_text: str) -> str:
    """Extract sender's first name if formatted as 'Customer (First Last <email>):'."""
    match = re.search(r"Customer\s*\(([^<]+)<", email_text)
    if match:
        full_name = match.group(1).strip()
        return full_name.split()[0]
    return ""


async def decide(email_text: str, has_attachments: bool = False) -> Decision:
    """Master decision entrypoint. Evaluates deterministic rules first, then AI engine."""
    subject = extract_subject_from_thread(email_text)
    sender_name = extract_sender_name(email_text)

    # 1. Mandatory escalation checks (safety, legal, attachments, prompt injection, anger)
    is_mandatory, reason = check_mandatory_escalation(
        email_text, has_attachments=has_attachments
    )
    if is_mandatory:
        greeting = f"Hi {sender_name or 'there'},"
        reply = (
            f"{greeting}\n\n"
            "Thank you for contacting Harbor & Pine. I have forwarded your message to a senior member of our support team "
            "so they can review your request and get back to you with next steps.\n\n"
            "Best regards,\nHarbor & Pine Support"
        )
        return Decision(
            action="escalate",
            section="escalation-rules",
            reply=reply,
            reason=reason,
            proposed_action="escalate",
        )

    # 2. Evaluate deterministic paddle-board rules
    pb_decision = evaluate_paddle_board_rules(email_text, subject, sender_name)
    if pb_decision:
        return pb_decision

    # 3. Evaluate deterministic shelving rules
    shelving_decision = evaluate_shelving_rules(email_text, subject, sender_name)
    if shelving_decision:
        return shelving_decision

    # 4. Evaluate general rules (shipping timelines, Amazon returns, late orders)
    general_decision = evaluate_general_rules(email_text, subject, sender_name)
    if general_decision:
        return general_decision

    # 5. Fallback to classifier + agent pipeline
    classification = await classify_email(email_text, subject)

    if classification.needs_human:
        return Decision(
            action="escalate",
            section=classification.section,
            reply=classification.acknowledgement,
            reason=classification.reason,
            proposed_action="escalate",
        )

    agent_reply = await generate_agent_reply(
        email_text, subject, section=classification.section
    )

    if agent_reply.action == "escalate" or not agent_reply.enough_information:
        return Decision(
            action="escalate",
            section=classification.section,
            reply=agent_reply.reply,
            reason=agent_reply.reasoning,
            proposed_action="escalate",
        )

    return Decision(
        action="reply",
        section=classification.section,
        reply=agent_reply.reply,
        reason=agent_reply.reasoning,
        proposed_action=None,
    )
