"""Unit tests for knowledge base markdown parsing and seeding."""

import app.db
from app.db import SQLiteMemoryDatabase
from scripts.seed_kb import parse_markdown_sections, seed_knowledge_base


def test_markdown_parsing(tmp_path):
    sample_md = tmp_path / "test-section.md"
    sample_md.write_text(
        "# Header 1\n\n## First Rule\nContent of first rule.\n\n## Second Rule\nContent of second rule.\n",
        encoding="utf-8",
    )
    entries = parse_markdown_sections(sample_md)
    assert len(entries) == 2
    assert entries[0][0] == "First Rule"
    assert entries[0][1] == "Content of first rule."
    assert entries[1][0] == "Second Rule"
    assert entries[1][1] == "Content of second rule."


def test_seed_knowledge_base_idempotence():
    test_db = SQLiteMemoryDatabase(":memory:")
    app.db._db_instance = test_db

    count1 = seed_knowledge_base()
    assert count1 >= 18  # Expected ~20 entries across 6 reference files

    sections = test_db.list_kb_sections()
    assert "paddle-boards" in sections
    assert "shelving" in sections
    assert "returns-and-warranty" in sections
    assert "shipping" in sections
    assert "brand-and-tone" in sections
    assert "escalation-rules" in sections

    # Running seed second time updates in place, creating zero duplicate rows
    count2 = seed_knowledge_base()
    assert count2 == count1
    all_entries = test_db.get_all_kb_entries()
    assert len(all_entries) == count1
