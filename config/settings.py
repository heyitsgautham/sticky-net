"""Application settings using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra env vars without error
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

    # AI Models (Gemini 3 with Gemini 2.5 fallback)
    flash_model: str = "gemini-3-flash-preview"  # Fast classification
    pro_model: str = "gemini-3-flash-preview"      # Engagement responses (primary)
    fallback_flash_model: str = "gemini-2.5-flash"  # Fallback classification
    fallback_pro_model: str = "gemini-2.5-pro"      # Fallback engagement
    llm_temperature: float = 0.7

    # API Timeout and Retry
    api_timeout_seconds: int = 90  # Increased from 60s to handle slow LLM responses
    gemini_max_retries: int = 2  # Number of retries on timeout
    gemini_retry_delay_seconds: float = 1.0  # Delay between retries

    # Engagement Policy
    max_engagement_turns_cautious: int = 10
    max_engagement_turns_aggressive: int = 25
    max_engagement_duration_seconds: int = 600
    cautious_confidence_threshold: float = 0.60
    aggressive_confidence_threshold: float = 0.85

    # Context Windowing (to reduce latency on deep conversations)
    context_window_turns: int = 8  # Limit conversation history to last N turns

    # Environment
    environment: str = "development"  # development, staging, production

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or console

    # Rate Limiting (production)
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # GUVI Callback Settings
    guvi_callback_url: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    guvi_callback_timeout: float = 10.0  # Timeout for callback requests in seconds
    guvi_callback_enabled: bool = True  # Flag to enable/disable callback

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
