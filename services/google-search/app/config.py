import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Settings for the Google Search Service."""
    GOOGLE_API_KEY: Optional[SecretStr] = Field(None, repr=False)
    GOOGLE_CSE_ID: Optional[str] = Field(None)
    DEFAULT_NUM_GOOGLE_RESULTS: int = Field(5, ge=1, le=10)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

settings = Settings()

if not all([settings.GOOGLE_API_KEY, settings.GOOGLE_CSE_ID]):
    logger.error("FATAL: GOOGLE_API_KEY or GOOGLE_CSE_ID is not configured. The service cannot function.")
else:
    logger.info("Google Search settings loaded successfully.")