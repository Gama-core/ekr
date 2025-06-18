import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Settings for the Quiz Generation Service."""
    APP_HOST: str = Field("0.0.0.0", description="Host to run the service on.")
    APP_PORT: int = Field(8004, description="Port to run the service on.")
    LLM_QUERY_SERVICE_URL: HttpUrl = Field("http://localhost:8002")

    QUIZ_MAX_TOKENS: int = Field(3072)
    QUIZ_DEFAULT_TEMPERATURE: float = Field(0.4, ge=0.0, le=2.0)
    QUIZ_MAX_QUESTIONS: int = Field(20, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )


settings = Settings()
logger.info(f"Quiz Service settings loaded. LLM Query Service URL: {settings.LLM_QUERY_SERVICE_URL}")