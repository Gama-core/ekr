# app/config.py
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    APP_HOST: str = Field("0.0.0.0")
    APP_PORT: int = Field(8000)
    DATABASE_API_URL: str
    SEMANTIC_RETRIEVAL_API_URL: str
    SUMMARY_API_URL: str
    FACT_CHECK_API_URL: str
    UPDATE_API_URL: str
    LLM_QUERY_SERVICE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()
# Optional: Update the log message
logger.info(f"API Gateway settings loaded with DB, RAG, Summary, FactCheck, and Update services.")

