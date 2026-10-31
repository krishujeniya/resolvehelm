"""Pytest configuration and global test fixtures."""

import os

import pytest

# Ensure tests run in testing mode with in-memory DB by default
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import app.db
from app.db import SQLiteMemoryDatabase


@pytest.fixture(autouse=True)
def reset_db_instance():
    """Ensure each test starts with a fresh in-memory database."""
    test_db = SQLiteMemoryDatabase(":memory:")
    app.db._db_instance = test_db
    yield test_db
    app.db._db_instance = None
