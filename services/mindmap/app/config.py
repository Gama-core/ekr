import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Settings for the Mindmap Generation Service."""
    LLM_QUERY_SERVICE_URL: HttpUrl = Field("http://localhost:8002")

    MINDMAP_MAX_TOKENS: int = Field(4096)
    MINDMAP_TEMPERATURE: float = Field(0.2, ge=0.0, le=2.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )


settings = Settings()
logger.info(f"Mindmap Service settings loaded. LLM Query Service URL: {settings.LLM_QUERY_SERVICE_URL}")