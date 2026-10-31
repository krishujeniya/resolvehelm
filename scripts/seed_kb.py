"""Seed Knowledge Base markdown files into the PostgreSQL/Supabase database."""

import logging
import re
import sys
from pathlib import Path

from app.db import get_db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("seed_kb")


def parse_markdown_sections(file_path: Path) -> list[tuple[str, str]]:
    """Parse a markdown file into a list of (title, content) tuples based on '## Heading'."""
    text = file_path.read_text(encoding="utf-8")
    entries: list[tuple[str, str]] = []

    # Split by level 2 headings: '## Heading'
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        # Fallback if no ## headings: treat entire document under file stem title
        entries.append((file_path.stem.replace("-", " ").title(), text.strip()))
        return entries

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start_idx:end_idx].strip()
        entries.append((title, content))

    return entries


def seed_knowledge_base() -> int:
    """Iterate over all .md files in knowledge_base directory and upsert into database."""
    kb_dir = Path(__file__).resolve().parent.parent / "knowledge_base"
    if not kb_dir.exists():
        logger.error("Knowledge base directory %s not found", kb_dir)
        sys.exit(1)

    db = get_db()
    total_seeded = 0

    md_files = sorted(kb_dir.glob("*.md"))
    for md_file in md_files:
        section = md_file.stem
        entries = parse_markdown_sections(md_file)
        logger.info("Seeding section '%s' (%d entries)...", section, len(entries))

        for title, content in entries:
            entry_id = db.upsert_kb_entry(section=section, title=title, content=content)
            logger.debug("Saved [%s] %s (id: %s)", section, title, entry_id)
            total_seeded += 1

    logger.info(
        "Successfully seeded %d knowledge base entries across %d sections.",
        total_seeded,
        len(md_files),
    )
    return total_seeded


if __name__ == "__main__":
    seed_knowledge_base()
