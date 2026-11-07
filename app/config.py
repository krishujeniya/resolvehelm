"""Application configuration and validation using Pydantic Settings."""

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ResolveHelm centralized configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment & Logging
    APP_ENV: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    DRY_RUN: bool = True
    AUTO_SEND_ENABLED: bool = False

    # Poller Settings
    POLL_INTERVAL_SECONDS: int = Field(default=30, ge=5, le=3600)
    MAX_MESSAGE_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    MAX_EMAIL_BODY_CHARS: int = Field(default=10000, ge=500, le=50000)
    MODEL_TIMEOUT_SECONDS: float = Field(default=30.0, ge=1.0, le=120.0)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/resolvehelm",
        description="PostgreSQL connection string",
    )

    # Gmail OAuth
    GOOGLE_CLIENT_ID: str = Field(default="", description="Google OAuth Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(
        default="", description="Google OAuth Client Secret"
    )
    GOOGLE_REFRESH_TOKEN: str = Field(
        default="", description="Google OAuth Refresh Token"
    )

    # AI Models
    AI_PROVIDER: Literal["anthropic", "gemini", "openai"] = Field(
        default="anthropic",
        description="Active AI model provider (anthropic, gemini, or openai)",
    )
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API Key")
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    CLASSIFIER_MODEL: str = Field(
        default="claude-3-5-haiku-latest",
        description="Model identifier for ticket classification",
    )
    AGENT_MODEL: str = Field(
        default="claude-3-5-sonnet-latest",
        description="Model identifier for agent reply drafting",
    )

    # Dashboard Authentication
    DASHBOARD_USERNAME: str = Field(default="admin", min_length=1)
    DASHBOARD_PASSWORD: str = Field(
        default="change-me-to-a-secure-password", min_length=6
    )

    # CORS Settings
    CORS_ALLOWED_ORIGINS: str = Field(
        default="*",
        description="Allowed CORS origins comma-separated or '*' for wildcard",
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "postgres://", "sqlite://")):
            raise ValueError(
                "DATABASE_URL must start with postgresql:// or postgres:// (or sqlite:// for tests)"
            )
        return v

    @model_validator(mode="after")
    def validate_production_guards(self) -> "Settings":
        """Enforce production security constraints."""
        if self.APP_ENV == "production":
            if self.DASHBOARD_PASSWORD in (
                "change-me-to-a-secure-password",
                "admin",
                "password",
                "",
            ):
                raise ValueError(
                    "DASHBOARD_PASSWORD cannot use default or blank value in production"
                )
            if (
                not self.GOOGLE_CLIENT_ID
                or not self.GOOGLE_CLIENT_SECRET
                or not self.GOOGLE_REFRESH_TOKEN
            ):
                raise ValueError(
                    "Google OAuth credentials must be provided in production"
                )
            if self.AI_PROVIDER == "anthropic" and not self.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY must be provided in production")
            elif self.AI_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY must be provided in production")
            elif self.AI_PROVIDER == "openai" and not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY must be provided in production")
        return self


def resolve_provider_model(model_name: str, provider: str = "anthropic") -> str:
    """Resolve model name into Pydantic AI provider-prefixed format."""
    if ":" in model_name:
        return model_name

    provider_clean = provider.strip().lower()
    if provider_clean == "gemini":
        return f"google:{model_name}"
    elif provider_clean == "openai":
        return f"openai:{model_name}"
    return f"anthropic:{model_name}"


# Global singleton settings instance
settings = Settings()

# Automatically sync GEMINI_API_KEY to os.environ for Pydantic AI Google provider
if settings.GEMINI_API_KEY:
    import os

    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
