"""Pre-processing guards preventing reply loops, self-replies, and bulk auto-responders."""

import logging

from app.gmail import ParsedEmail

logger = logging.getLogger(__name__)


def should_skip_message(
    email: ParsedEmail,
    support_email: str = "",
) -> tuple[bool, str]:
    """Inspect email headers and sender to determine if message must be skipped safely.

    Returns:
        (should_skip: bool, skip_reason: str)
    """
    # 1. Skip if missing sender
    if not email.sender or not email.sender.strip():
        return True, "Missing sender address."

    # 2. Skip if sent by the support account itself (prevent infinite self-reply loops)
    sender_clean = email.sender.lower()
    if support_email and support_email.lower() in sender_clean:
        return True, "Message sent by support mailbox itself."

    # 3. Skip automated system messages, bounces, newsletters, or auto-replies
    if email.is_automated:
        return (
            True,
            "Automated or system generated email (Auto-Submitted, bulk, or no-reply).",
        )

    # 4. Skip empty subject and empty body
    if not email.subject.strip() and not email.body.strip():
        return True, "Message has both empty subject and empty body."

    return False, ""
