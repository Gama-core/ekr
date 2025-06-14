import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Settings for the RSS Extractor Service."""
    FEED_FETCH_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Default timeout in seconds for fetching an RSS feed."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

settings = Settings()
logger.info(f"RSS Extractor settings loaded. Fetch timeout: {settings.FEED_FETCH_TIMEOUT_SECONDS}s.")