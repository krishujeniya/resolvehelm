"""Background polling engine monitoring Gmail inbox and triggering processing pipeline."""

import asyncio
import logging
import signal
from typing import Any

from app.config import settings
from app.db import BaseDatabase, get_db
from app.gmail import GmailClient
from app.pipeline import process_email_message

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("poller")


async def poll_once(
    gmail_client: Any | None = None,
    db: BaseDatabase | None = None,
) -> int:
    """Run a single polling cycle over unprocessed messages in the Gmail inbox."""
    if gmail_client is None:
        gmail_client = GmailClient()
    if db is None:
        db = get_db()

    logger.debug("Checking inbox for unprocessed customer emails...")
    messages = gmail_client.list_unprocessed_inbox_messages(max_results=20)
    if not messages:
        logger.debug("No unprocessed messages found in inbox.")
        return 0

    logger.info("Discovered %d unprocessed message(s) in inbox.", len(messages))
    processed_count = 0

    for item in messages:
        msg_id = item["id"]
        thread_id = item.get("threadId", msg_id)
        try:
            res = await process_email_message(
                message_id=msg_id,
                thread_id=thread_id,
                gmail_client=gmail_client,
                db=db,
            )
            if res.get("status") in ("completed", "skipped"):
                processed_count += 1
        except Exception as e:
            logger.error("Failed to process message %s in polling cycle: %s", msg_id, e)
            # Continue processing subsequent messages in batch rather than aborting poller

    logger.info(
        "Completed poll cycle: processed %d/%d messages.",
        processed_count,
        len(messages),
    )
    return processed_count


async def run_poller():
    """Continuous background polling loop with graceful shutdown support."""
    logger.info(
        "Starting ResolveHelm inbox poller (interval: %ds, dry_run: %s, auto_send: %s)...",
        settings.POLL_INTERVAL_SECONDS,
        settings.DRY_RUN,
        settings.AUTO_SEND_ENABLED,
    )

    gmail_client = GmailClient()
    db = get_db()
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: stop_event.set())
        except (NotImplementedError, RuntimeError):
            pass

    while not stop_event.is_set():
        try:
            await poll_once(gmail_client=gmail_client, db=db)
        except Exception as e:
            logger.exception("Unexpected error during poll cycle: %s", e)

        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=float(settings.POLL_INTERVAL_SECONDS)
            )
        except TimeoutError:
            pass

    logger.info("ResolveHelm poller stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(run_poller())
