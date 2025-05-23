# app/features/google_search/config.py
from pydantic import BaseModel, Field

class GoogleSearchFeatureSettings(BaseModel):
    DEFAULT_NUM_GOOGLE_RESULTS: int = Field(default=5, description="Default number of results for Google search.")

# Global instance of Google Search operational settings.
google_search_settings = GoogleSearchFeatureSettings()