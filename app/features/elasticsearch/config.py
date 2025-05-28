# app/features/elasticsearch/config.py
from pydantic import BaseModel, Field
from app.core.config import settings as core_global_settings # Import the final global settings instance
import logging
from typing import Optional, List # Added Optional and List

logger = logging.getLogger(__name__)

class ElasticsearchFeatureSettings(BaseModel):
    """
    Configuration specific to the Elasticsearch feature.
    It primarily sources its values from the global core settings.
    """
    # For direct host connection (e.g., self-managed, AWS OpenSearch without Cloud ID)
    ES_HOST_URL: Optional[str] = Field( # Make Optional as it might not be used if CLOUD_ID is primary
        default_factory=lambda: core_global_settings.ES_HOST,
        description="The complete URL for the Elasticsearch instance (e.g., 'http://localhost:9200' or 'https://...')."
    )
    INDEX_NAME: str = Field(
        default_factory=lambda: core_global_settings.ES_INDEX_NAME,
        description="Default index name for notes within Elasticsearch."
    )

    # For Elastic Cloud connection (using Cloud ID and API Key)
    ES_CLOUD_ID: Optional[str] = Field(
        default_factory=lambda: core_global_settings.ES_CLOUD_ID,
        description="Elastic Cloud ID for connection."
    )
    ES_API_KEY_ID: Optional[str] = Field(
        default_factory=lambda: core_global_settings.ES_API_KEY_ID,
        description="API Key ID for Elastic Cloud authentication."
    )
    ES_API_KEY: Optional[str] = Field(
        default_factory=lambda: core_global_settings.ES_API_KEY,
        description="Secret API Key for Elastic Cloud authentication.",
        repr=False # Ensure secret is not exposed in logs/repr
    )

    # For basic authentication with ES_HOST_URL
    ES_USERNAME: Optional[str] = Field(
        default_factory=lambda: core_global_settings.ES_USERNAME,
        description="Username for basic authentication with Elasticsearch."
    )
    ES_PASSWORD: Optional[str] = Field(
        default_factory=lambda: core_global_settings.ES_PASSWORD,
        description="Password for basic authentication with Elasticsearch.",
        repr=False # Ensure secret is not exposed in logs/repr
    )


    @property
    def HOSTS_LIST(self) -> List[str]: # Type hint changed to List[str]
        """
        Provides the ES_HOST_URL as a list, which is what the
        ElasticsearchService might expect if it's designed for multiple hosts
        and not using Cloud ID.
        """
        if self.ES_HOST_URL: # Only return if ES_HOST_URL is set
            return [self.ES_HOST_URL]
        # If CLOUD_ID is used, HOSTS_LIST is not typically needed by the ES client,
        # so returning an empty list is fine if ES_HOST_URL is not set.
        return []


# Global instance of Elasticsearch feature-specific operational settings.
# This instance will be created when this module is imported.
elasticsearch_settings = ElasticsearchFeatureSettings()

# Log the settings that will be used by the Elasticsearch feature
# Be careful not to log sensitive values directly
logger.info(f"Elasticsearch Feature Settings Initialized:")
if elasticsearch_settings.ES_CLOUD_ID:
    logger.info(f"  ES_CLOUD_ID (from core): {'******' if elasticsearch_settings.ES_CLOUD_ID else None}") # Mask or show prefix
    logger.info(f"  ES_API_KEY_ID (from core): {elasticsearch_settings.ES_API_KEY_ID}")
    logger.info(f"  ES_API_KEY (from core) Present: {'Yes' if elasticsearch_settings.ES_API_KEY else 'No'}")
elif elasticsearch_settings.ES_HOST_URL:
    logger.info(f"  ES_HOST_URL (from core): {elasticsearch_settings.ES_HOST_URL}")
    if elasticsearch_settings.ES_USERNAME:
        logger.info(f"  ES_USERNAME (from core): {elasticsearch_settings.ES_USERNAME}")
        logger.info(f"  ES_PASSWORD (from core) Present: {'Yes' if elasticsearch_settings.ES_PASSWORD else 'No'}")
    logger.info(f"  HOSTS_LIST for ES client (if applicable): {elasticsearch_settings.HOSTS_LIST}")
else:
    logger.warning("  Elasticsearch connection details (Cloud ID or Host URL) not configured in feature settings.")

logger.info(f"  INDEX_NAME (from core): {elasticsearch_settings.INDEX_NAME}")