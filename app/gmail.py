"""Gmail API integration, MIME parsing, label management, and thread formatting."""

import base64
import logging
import re
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)

# Required system labels
LABEL_AI_PROCESSED = "ai-processed"
LABEL_NEEDS_HUMAN = "needs-human"


@dataclass
class ParsedEmail:
    """Structured representation of an incoming or outgoing email message."""

    message_id: str
    thread_id: str
    sender: str
    recipient: str
    subject: str
    body: str
    date: str
    rfc_message_id: str = ""
    in_reply_to: str = ""
    references: str = ""
    has_attachments: bool = False
    attachment_names: list[str] = field(default_factory=list)
    is_automated: bool = False
    raw_headers: dict[str, str] = field(default_factory=dict)


def clean_quoted_history(body: str) -> str:
    """Strip or isolate trailing quoted email history (e.g. 'On ... wrote:')."""
    lines = body.splitlines()
    cleaned: list[str] = []
    quote_patterns = [
        re.compile(r"^On\s.+wrote:$", re.IGNORECASE),
        re.compile(r"^From:\s.+", re.IGNORECASE),
        re.compile(r"^[-]{2,}\s*Original Message\s*[-]{2,}", re.IGNORECASE),
        re.compile(r"^Begin forwarded message:", re.IGNORECASE),
    ]

    for line in lines:
        if any(pattern.match(line.strip()) for pattern in quote_patterns):
            break
        if line.strip().startswith(">"):
            continue
        cleaned.append(line)

    result = "\n".join(cleaned).strip()
    return result if result else body.strip()


def is_automated_sender(headers: dict[str, str]) -> bool:
    """Detect automated emails (auto-replies, bounces, mailing lists, newsletters)."""
    headers_lower = {k.lower(): v.lower() for k, v in headers.items()}

    # Standard auto-submitted header (RFC 3834)
    auto_submitted = headers_lower.get("auto-submitted", "")
    if auto_submitted and auto_submitted != "no":
        return True

    # Precedence bulk/list/junk
    precedence = headers_lower.get("precedence", "")
    if precedence in ("bulk", "list", "junk", "auto_reply"):
        return True

    # Mailing list indicators
    if "list-id" in headers_lower or "list-unsubscribe" in headers_lower:
        return True

    # Common automated sender addresses
    from_header = headers_lower.get("from", "")
    automated_prefixes = (
        "no-reply@",
        "noreply@",
        "mailer-daemon@",
        "postmaster@",
        "notifications@",
        "alert@",
    )
    return any(
        from_header.startswith(prefix) or f"<{prefix}" in from_header
        for prefix in automated_prefixes
    )


def extract_header(headers_list: list[dict[str, str]], name: str) -> str:
    """Case-insensitive header extraction from Gmail API payload headers."""
    target = name.lower()
    for h in headers_list:
        if h.get("name", "").lower() == target:
            return h.get("value", "")
    return ""


def parse_mime_payload(payload: dict[str, Any]) -> tuple[str, bool, list[str]]:
    """Recursively decode text bodies and detect attachments from a Gmail message payload."""
    body_text = ""
    has_attachments = False
    attachment_names: list[str] = []

    mime_type = payload.get("mimeType", "")
    filename = payload.get("filename", "")
    if filename:
        has_attachments = True
        attachment_names.append(filename)

    parts = payload.get("parts", [])
    if parts:
        for part in parts:
            part_body, part_has_attach, part_attach_names = parse_mime_payload(part)
            if part_has_attach:
                has_attachments = True
                attachment_names.extend(part_attach_names)
            if not body_text and part_body:
                body_text = part_body
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(data.encode("ASCII")).decode(
                    "utf-8", errors="replace"
                )
                if mime_type == "text/plain":
                    body_text = decoded
                elif mime_type == "text/html" and not body_text:
                    # Strip simple HTML tags for plain text fallback
                    body_text = re.sub(r"<[^>]+>", " ", decoded)
                    body_text = re.sub(r"\s+", " ", body_text).strip()
            except Exception as e:
                logger.warning("Failed to decode message part: %s", e)

    return body_text, has_attachments, attachment_names


def parse_gmail_message(msg_data: dict[str, Any]) -> ParsedEmail:
    """Parse raw Gmail API response dict into structured ParsedEmail."""
    msg_id = msg_data.get("id", "")
    thread_id = msg_data.get("threadId", "")
    payload = msg_data.get("payload", {})
    headers_list = payload.get("headers", [])

    raw_headers = {h.get("name", ""): h.get("value", "") for h in headers_list}

    sender = extract_header(headers_list, "From")
    recipient = extract_header(headers_list, "To")
    subject = extract_header(headers_list, "Subject")
    date = extract_header(headers_list, "Date")
    rfc_message_id = extract_header(headers_list, "Message-ID")
    in_reply_to = extract_header(headers_list, "In-Reply-To")
    references = extract_header(headers_list, "References")

    body, has_attachments, attachment_names = parse_mime_payload(payload)
    if not body:
        body = msg_data.get("snippet", "")

    cleaned_body = clean_quoted_history(body)
    is_auto = is_automated_sender(raw_headers)

    return ParsedEmail(
        message_id=msg_id,
        thread_id=thread_id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        body=cleaned_body,
        date=date,
        rfc_message_id=rfc_message_id,
        in_reply_to=in_reply_to,
        references=references,
        has_attachments=has_attachments,
        attachment_names=attachment_names,
        is_automated=is_auto,
        raw_headers=raw_headers,
    )


def format_thread_for_ai(messages: list[ParsedEmail], support_email: str = "") -> str:
    """Format full email thread chronologically for AI context."""
    if not messages:
        return ""

    subject = messages[0].subject or "Support inquiry"
    formatted_parts = [f"Subject: {subject}\n"]

    for msg in messages:
        sender_lower = msg.sender.lower()
        if support_email and support_email.lower() in sender_lower:
            speaker = f"Support ({msg.sender})"
        else:
            speaker = f"Customer ({msg.sender})"

        formatted_parts.append(f"{speaker}:\n{msg.body.strip()}\n")

    return "\n".join(formatted_parts).strip()


class GmailClient:
    """Gmail API client managing message fetching, labeling, and replies."""

    def __init__(self, service: Any | None = None) -> None:
        self._service = service
        self._label_cache: dict[str, str] = {}
        self._support_email: str = ""

    @property
    def service(self) -> Any:
        if self._service is None:
            self._service = self._init_service()
        return self._service

    def _init_service(self) -> Any:
        """Initialize Google Gmail API client using OAuth refresh token."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REFRESH_TOKEN:
            raise ValueError(
                "Gmail credentials (GOOGLE_CLIENT_ID, GOOGLE_REFRESH_TOKEN) are not configured."
            )

        creds = Credentials(
            token=None,
            refresh_token=settings.GOOGLE_REFRESH_TOKEN,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
        )
        creds.refresh(Request())
        return build("gmail", "v1", credentials=creds)

    def get_support_email(self) -> str:
        """Retrieve and cache the authenticated mailbox user's email address."""
        if not self._support_email:
            try:
                profile = self.service.users().getProfile(userId="me").execute()
                self._support_email = profile.get("emailAddress", "")
            except Exception as e:
                logger.warning("Could not fetch user profile: %s", e)
        return self._support_email

    def get_or_create_label(self, label_name: str) -> str:
        """Retrieve label ID by name, creating it if it does not exist."""
        if label_name in self._label_cache:
            return self._label_cache[label_name]

        try:
            labels_resp = self.service.users().labels().list(userId="me").execute()
            for label in labels_resp.get("labels", []):
                if label.get("name", "").lower() == label_name.lower():
                    self._label_cache[label_name] = label["id"]
                    return label["id"]

            # Create label if not found
            created = (
                self.service.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": label_name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )
            self._label_cache[label_name] = created["id"]
            return created["id"]
        except Exception as e:
            logger.error("Failed to get or create label %s: %s", label_name, e)
            raise

    def list_unprocessed_inbox_messages(
        self, max_results: int = 20
    ) -> list[dict[str, str]]:
        """List eligible inbox messages not yet marked ai-processed or needs-human."""
        query = f"in:inbox -label:{LABEL_AI_PROCESSED} -label:{LABEL_NEEDS_HUMAN}"
        try:
            resp = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            return resp.get("messages", [])
        except Exception as e:
            logger.error("Failed to list unprocessed inbox messages: %s", e)
            return []

    def get_message(self, message_id: str) -> ParsedEmail:
        """Fetch raw message by ID and parse it into structured ParsedEmail."""
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return parse_gmail_message(raw)

    def get_thread(self, thread_id: str) -> list[ParsedEmail]:
        """Fetch all messages belonging to a thread and return ordered ParsedEmail list."""
        raw_thread = (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        messages_raw = raw_thread.get("messages", [])
        return [parse_gmail_message(m) for m in messages_raw]

    def build_reply_mime(
        self,
        to_email: str,
        subject: str,
        body: str,
        rfc_message_id: str = "",
        thread_id: str = "",
    ) -> dict[str, Any]:
        """Construct raw RFC-2822 reply MIME message with proper threading headers."""
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to_email
        msg["Subject"] = (
            subject if subject.lower().startswith("re:") else f"Re: {subject}"
        )

        if rfc_message_id:
            msg["In-Reply-To"] = rfc_message_id
            msg["References"] = rfc_message_id

        raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("ASCII")
        payload: dict[str, Any] = {"raw": raw_b64}
        if thread_id:
            payload["threadId"] = thread_id
        return payload

    def send_reply(self, mime_payload: dict[str, Any]) -> dict[str, Any]:
        """Send email reply via Gmail API, respecting DRY_RUN configuration."""
        if settings.DRY_RUN or not settings.AUTO_SEND_ENABLED:
            logger.info(
                "DRY_RUN or AUTO_SEND_ENABLED=False. Simulating send: %s",
                mime_payload.get("threadId"),
            )
            return {
                "id": "dry-run-" + mime_payload.get("threadId", "simulated"),
                "threadId": mime_payload.get("threadId", ""),
                "simulated": True,
            }

        try:
            return (
                self.service.users()
                .messages()
                .send(userId="me", body=mime_payload)
                .execute()
            )
        except Exception as e:
            logger.error("Failed to send reply: %s", e)
            raise

    def apply_label(self, message_id: str, label_name: str) -> None:
        """Attach a label to a Gmail message."""
        label_id = self.get_or_create_label(label_name)
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id]},
            ).execute()
            logger.info(
                "Applied label '%s' (%s) to message %s",
                label_name,
                label_id,
                message_id,
            )
        except Exception as e:
            logger.error(
                "Failed to apply label '%s' to message %s: %s",
                label_name,
                message_id,
                e,
            )
            raise


class MockGmailClient:
    """In-memory mock client for tests and dry-run development."""

    def __init__(
        self, support_email: str = "support@harborandpine.example.com"
    ) -> None:
        self.support_email = support_email
        self.inbox: dict[str, ParsedEmail] = {}
        self.threads: dict[str, list[ParsedEmail]] = {}
        self.labels: dict[str, set[str]] = {}  # msg_id -> set of label_names
        self.sent_messages: list[dict[str, Any]] = []

    def get_support_email(self) -> str:
        return self.support_email

    def get_or_create_label(self, label_name: str) -> str:
        return f"label-id-{label_name}"

    def add_mock_message(self, email: ParsedEmail) -> None:
        self.inbox[email.message_id] = email
        if email.thread_id not in self.threads:
            self.threads[email.thread_id] = []
        self.threads[email.thread_id].append(email)
        if email.message_id not in self.labels:
            self.labels[email.message_id] = set()

    def list_unprocessed_inbox_messages(
        self, max_results: int = 20
    ) -> list[dict[str, str]]:
        results = []
        for msg_id, email in self.inbox.items():
            msg_labels = self.labels.get(msg_id, set())
            if (
                LABEL_AI_PROCESSED not in msg_labels
                and LABEL_NEEDS_HUMAN not in msg_labels
            ):
                results.append({"id": msg_id, "threadId": email.thread_id})
            if len(results) >= max_results:
                break
        return results

    def get_message(self, message_id: str) -> ParsedEmail:
        if message_id not in self.inbox:
            raise KeyError(f"Message {message_id} not found")
        return self.inbox[message_id]

    def get_thread(self, thread_id: str) -> list[ParsedEmail]:
        return self.threads.get(thread_id, [])

    def build_reply_mime(
        self,
        to_email: str,
        subject: str,
        body: str,
        rfc_message_id: str = "",
        thread_id: str = "",
    ) -> dict[str, Any]:
        return {
            "to": to_email,
            "subject": subject,
            "body": body,
            "rfc_message_id": rfc_message_id,
            "threadId": thread_id,
        }

    def send_reply(self, mime_payload: dict[str, Any]) -> dict[str, Any]:
        result = {
            "id": f"sent-{len(self.sent_messages) + 1}",
            "threadId": mime_payload.get("threadId", ""),
            "to": mime_payload.get("to", ""),
            "subject": mime_payload.get("subject", ""),
            "body": mime_payload.get("body", ""),
            "simulated": True,
        }
        self.sent_messages.append(result)
        return result

    def apply_label(self, message_id: str, label_name: str) -> None:
        if message_id not in self.labels:
            self.labels[message_id] = set()
        self.labels[message_id].add(label_name)
