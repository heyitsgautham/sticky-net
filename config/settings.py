"""Application settings using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    api_key: str
    port: int = 8080
    debug: bool = False

    # Google Cloud
    google_cloud_project: str
    google_cloud_location: str = "global"
    google_genai_use_vertexai: bool = True
    google_application_credentials: str | None = None

    # Firestore
    firestore_collection: str = "conversations"
    firestore_emulator_host: str | None = None

    # AI Models (Gemini 3)
    flash_model: str = "gemini-3-flash-preview"  # Fast classification
    pro_model: str = "gemini-3-pro-preview"      # Engagement responses
    llm_temperature: float = 0.7

    # Engagement Policy
    max_engagement_turns_cautious: int = 10
    max_engagement_turns_aggressive: int = 25
    max_engagement_duration_seconds: int = 600
    cautious_confidence_threshold: float = 0.60
    aggressive_confidence_threshold: float = 0.85


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
