"""Unit tests for application configuration."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_default_settings(monkeypatch):
    """Verify default development settings initialize properly."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    cfg = Settings()
    assert cfg.APP_ENV == "development"
    assert cfg.DRY_RUN is True
    assert cfg.AUTO_SEND_ENABLED is False
    assert cfg.POLL_INTERVAL_SECONDS == 30
    assert cfg.MAX_MESSAGE_ATTEMPTS == 3
    assert cfg.DASHBOARD_USERNAME == "admin"


def test_invalid_polling_interval():
    """Verify invalid polling intervals are rejected."""
    with pytest.raises(ValidationError):
        Settings(POLL_INTERVAL_SECONDS=2)  # ge=5 is required


def test_invalid_database_url():
    """Verify non-database URLs are rejected."""
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="mysql://root@localhost/db")


def test_production_password_guard():
    """Verify weak dashboard password raises error in production."""
    with pytest.raises(ValidationError, match="DASHBOARD_PASSWORD cannot use default"):
        Settings(
            APP_ENV="production",
            DASHBOARD_PASSWORD="change-me-to-a-secure-password",
            GOOGLE_CLIENT_ID="dummy-id",
            GOOGLE_CLIENT_SECRET="dummy-secret",
            GOOGLE_REFRESH_TOKEN="dummy-token",
            ANTHROPIC_API_KEY="dummy-key",
        )


def test_resolve_provider_model():
    from app.config import resolve_provider_model

    # Default Anthropic
    assert (
        resolve_provider_model("claude-3-5-haiku-latest", "anthropic")
        == "anthropic:claude-3-5-haiku-latest"
    )

    # Gemini provider
    assert (
        resolve_provider_model("gemini-3.5-flash-lite", "gemini")
        == "google:gemini-3.5-flash-lite"
    )

    # OpenAI provider
    assert resolve_provider_model("gpt-4o", "openai") == "openai:gpt-4o"

    # Already prefixed
    assert (
        resolve_provider_model("google-vertex:gemini-1.5-pro", "gemini")
        == "google-vertex:gemini-1.5-pro"
    )


def test_production_provider_key_guard():
    with pytest.raises(ValidationError, match="GEMINI_API_KEY must be provided"):
        Settings(
            APP_ENV="production",
            AI_PROVIDER="gemini",
            DASHBOARD_PASSWORD="super-secret-production-password",
            GOOGLE_CLIENT_ID="dummy-id",
            GOOGLE_CLIENT_SECRET="dummy-secret",
            GOOGLE_REFRESH_TOKEN="dummy-token",
            ANTHROPIC_API_KEY="dummy-key",
            GEMINI_API_KEY="",
        )
