# services/elasticsearch-service/app/features/elasticsearch/config.py
import logging
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Configuration for the Elasticsearch Service.
    Loads settings from environment variables or a .env file.
    """
    # URL to fetch data from
    DATABASE_API_URL: Optional[str] = Field(None)

    # Elasticsearch Connection Settings
    ES_INDEX_NAME: str = Field(default="notes_index")
    ES_HOST_URL: Optional[str] = Field(default=None)
    ES_USERNAME: Optional[str] = Field(default=None)
    ES_PASSWORD: Optional[str] = Field(default=None, repr=False)
    ES_CLOUD_ID: Optional[str] = Field(default=None)
    ES_API_KEY_ID: Optional[str] = Field(default=None)
    ES_API_KEY: Optional[str] = Field(default=None, repr=False)

    @property
    def HOSTS_LIST(self) -> List[str]:
        return [self.ES_HOST_URL] if self.ES_HOST_URL else []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra='ignore',
        case_sensitive=False
    )

settings = Settings()

logger.info("--- Elasticsearch Service Settings Initialized ---")
if settings.DATABASE_API_URL:
    logger.info(f"  Target Database API URL: {settings.DATABASE_API_URL}")
else:
    logger.critical("  DATABASE_API_URL is NOT SET. Service cannot function.")

if settings.ES_CLOUD_ID:
    logger.info(f"  ES Connection: Elastic Cloud")
elif settings.ES_HOST_URL:
    logger.info(f"  ES Connection: Direct Host ({settings.ES_HOST_URL})")
else:
    logger.warning("  Elasticsearch connection details not configured.")

# --- THIS IS THE CORRECTED LINE ---
logger.info(f"  ES Index Name: {settings.ES_INDEX_NAME}")
logger.info("-------------------------------------------------")