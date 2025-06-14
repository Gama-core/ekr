# services/database-api/app/config.py
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Settings for the Database API Service.
    Pydantic-settings automatically prioritizes environment variables over .env file values.
    """
    DB_HOST: Optional[str] = Field(None)
    DB_PORT: Optional[str] = Field("5432")
    DB_USER: Optional[str] = Field(None)
    DB_PASSWORD: Optional[SecretStr] = Field(None, repr=False)
    DB_NAME: Optional[str] = Field(None)

    model_config = SettingsConfigDict(
        env_file=".env",  # Look for .env in the parent directory
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )

# Create a single, importable instance of the settings
settings = Settings()

# Log feedback about the loaded settings
if not all([settings.DB_HOST, settings.DB_PORT, settings.DB_USER, settings.DB_NAME, settings.DB_PASSWORD]):
    logger.warning("One or more database connection parameters are missing. Database connection will likely fail.")
else:
    logger.info(f"Database settings loaded for host: {settings.DB_HOST}")