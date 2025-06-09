# app/features/rss_extractor/config.py
from pydantic import BaseModel, Field

class RssExtractorSettings(BaseModel):
    FEED_FETCH_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout in seconds for fetching the RSS feed."
    )

rss_extractor_settings = RssExtractorSettings()