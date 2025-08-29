import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, HttpUrl

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Settings for the OCR Service."""
    APP_HOST: str = Field("0.0.0.0")
    APP_PORT: int = Field(8005)  # This acts as a default

    MISTRAL_API_KEY: Optional[SecretStr] = Field(None, repr=False)
    MISTRAL_API_BASE_URL: HttpUrl = Field("https://api.mistral.ai")
    MISTRAL_OCR_DEFAULT_MODEL: str = Field("mistral-ocr-latest")

    OCR_TIMEOUT_SECONDS: int = Field(90)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )


settings = Settings()

if not settings.MISTRAL_API_KEY:
    logger.error("FATAL: MISTRAL_API_KEY is not configured. The OCR service cannot function.")
else:
    logger.info("OCR Service settings loaded successfully.")