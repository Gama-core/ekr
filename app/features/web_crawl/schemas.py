# app/features/web_crawl/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal

# --- Web Crawling Schemas ---
class SingleUrlCrawlRequest(BaseModel):
    url: HttpUrl = Field(..., description="The URL to crawl.")

class CrawlStatus(BaseModel): # Common status fields for crawl operations.
    status: Literal["success", "failed", "pending"] = Field(..., description="Status of the crawl attempt.")
    content_markdown: Optional[str] = Field(None, description="Extracted content in Markdown.")
    title: Optional[str] = Field(None, description="Extracted/generated title of the page.")
    error_message: Optional[str] = Field(None, description="Error message if crawling failed.")

class SingleUrlCrawlResponse(CrawlStatus): # Response for single URL crawl.
    url: HttpUrl = Field(..., description="The URL that was crawled.")

class MultipleUrlsCrawlRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., description="A list of URLs to crawl.", min_length=1)
# Response for MultipleUrlsCrawlRequest is List[SingleUrlCrawlResponse].