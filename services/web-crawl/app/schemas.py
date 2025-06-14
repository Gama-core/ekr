from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal

class SingleUrlCrawlRequest(BaseModel):
    url: HttpUrl

class CrawlStatus(BaseModel):
    status: Literal["success", "failed", "pending"]
    content_markdown: Optional[str] = None
    title: Optional[str] = None
    error_message: Optional[str] = None

class SingleUrlCrawlResponse(CrawlStatus):
    url: HttpUrl

class MultipleUrlsCrawlRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., min_length=1)