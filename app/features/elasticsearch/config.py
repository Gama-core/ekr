# app/features/elasticsearch/config.py
from pydantic import BaseModel, Field
from app.core.config import settings as core_global_settings # Import the final global settings instance
import logging

logger = logging.getLogger(__name__)

class ElasticsearchFeatureSettings(BaseModel):
    """
    Configuration specific to the Elasticsearch feature.
    It primarily sources its values from the global core settings.
    """
    # The HOSTS field should be a list of full URLs for the Elasticsearch client.
    # We will derive this from the core_global_settings.ES_HOST.
    # The elasticsearch-py client can take a single string URL or a list of string URLs.
    # For simplicity, we'll assume ES_HOST from core settings is a single, complete URL.
    # If ES_HOST could be a comma-separated list, more parsing would be needed here.
    ES_HOST_URL: str = Field(
        default_factory=lambda: core_global_settings.ES_HOST,
        description="The complete URL for the Elasticsearch instance (e.g., 'http://localhost:9200')."
    )
    INDEX_NAME: str = Field(
        default_factory=lambda: core_global_settings.ES_INDEX_NAME,
        description="Default index name for notes within Elasticsearch."
    )

    @property
    def HOSTS_LIST(self) -> list[str]:
        """
        Provides the ES_HOST_URL as a list, which is what the
        ElasticsearchService might expect if it's designed for multiple hosts.
        """
        if not self.ES_HOST_URL:
            logger.error("ES_HOST_URL is not configured in ElasticsearchFeatureSettings.")
            return [] # Return empty list if not configured to prevent errors
        return [self.ES_HOST_URL]


# Global instance of Elasticsearch feature-specific operational settings.
# This instance will be created when this module is imported.
elasticsearch_settings = ElasticsearchFeatureSettings()

# Log the settings that will be used by the Elasticsearch feature
logger.info(f"Elasticsearch Feature Settings Initialized:")
logger.info(f"  ES_HOST_URL (derived from core): {elasticsearch_settings.ES_HOST_URL}")
logger.info(f"  INDEX_NAME (derived from core): {elasticsearch_settings.INDEX_NAME}")
logger.info(f"  HOSTS_LIST for ES client: {elasticsearch_settings.HOSTS_LIST}")