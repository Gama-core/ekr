# app/features/web_interaction/config.py
from pydantic import BaseModel

# Defines feature-specific settings for web interaction tasks.
class WebInteractionSettings(BaseModel):
    DEFAULT_NUM_GOOGLE_RESULTS: int = 5
    DEFAULT_NUM_RESULTS_TO_CRAWL: int = 3
    CRAWL_TIMEOUT_SECONDS: int = 60
    MAX_CRAWL_CONTENT_LENGTH: int = 100000 # Max characters for crawled content.

# Global instance of web interaction settings.
web_interaction_settings = WebInteractionSettings()