# app/features/web_crawl/config.py
from pydantic import BaseModel, Field

class WebCrawlFeatureSettings(BaseModel):
    CRAWL_TIMEOUT_SECONDS: int = Field(default=60, description="Timeout in seconds for a single crawl operation.")
    MAX_CRAWL_CONTENT_LENGTH: int = Field(default=30000, description="Max characters for crawled content to be returned. Content will be truncated if it exceeds this.") # Increased default

# Global instance of web crawl operational settings.
web_crawl_settings = WebCrawlFeatureSettings()