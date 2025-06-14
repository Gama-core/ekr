import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Settings for the LLM Query Service.
    Loads API keys and default model parameters from environment or .env file.
    """
    QWEN_API_KEY: Optional[SecretStr] = Field(None, repr=False)
    QWEN_BASE_URL: Optional[str] = Field("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus")

    DEFAULT_MAX_TOKENS: int = Field(2048)
    DEFAULT_TEMPERATURE: float = Field(0.7, ge=0.0, le=2.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

settings = Settings()

if not settings.QWEN_API_KEY:
    logger.error("FATAL: QWEN_API_KEY is not configured. The LLM service cannot function.")
else:
    logger.info(f"LLM settings loaded. Default model: {settings.QWEN_DEFAULT_MODEL}, Base URL: {settings.QWEN_BASE_URL}")