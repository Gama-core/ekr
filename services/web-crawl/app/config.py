import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Settings for the Web Crawl Service."""
    APP_HOST: str
    APP_PORT: int

    CRAWL_TIMEOUT_SECONDS: int = Field(60)
    MAX_CRAWL_CONTENT_LENGTH: int = Field(30000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )


settings = Settings()
logger.info(
    f"Web Crawl settings loaded. Timeout: {settings.CRAWL_TIMEOUT_SECONDS}s, Max Length: {settings.MAX_CRAWL_CONTENT_LENGTH} chars.")