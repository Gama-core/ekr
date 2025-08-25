import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Settings for the Fact Check Service."""
    APP_HOST: str = Field("0.0.0.0", description="Host to run the service on.")
    APP_PORT: int = Field(8008, description="Port to run the service on.")
    LLM_QUERY_SERVICE_URL: HttpUrl = Field("http://localhost:8002")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

settings = Settings()
logger.info(f"Fact Check Service settings loaded. LLM Query Service URL: {settings.LLM_QUERY_SERVICE_URL}")