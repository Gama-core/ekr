# app/features/web_interaction/config.py
from pydantic import BaseModel, Field



# API keys for Google Search are available via the global core settings.
class WebInteractionFeatureSettings(BaseModel):
    DEFAULT_NUM_GOOGLE_RESULTS: int = 5
    DEFAULT_NUM_RESULTS_TO_CRAWL: int = 3
    CRAWL_TIMEOUT_SECONDS: int = 60
    MAX_CRAWL_CONTENT_LENGTH: int = 1000 # Max characters for crawled content.

# Global instance of web interaction operational settings.
web_interaction_settings = WebInteractionFeatureSettings()


