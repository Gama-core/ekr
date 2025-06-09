# app/features/rss_extractor/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
import datetime


# --- Request Schema ---
class RssFeedRequest(BaseModel):
    url: HttpUrl = Field(..., description="The URL of the RSS or Atom feed.")


# --- Nested Schema for Response ---
class RssEntryItem(BaseModel):
    title: Optional[str] = Field(None, description="The title of the feed entry.")
    link: HttpUrl = Field(..., description="The primary URL/link from the feed entry.")
    summary: Optional[str] = Field(None, description="The summary or description of the entry.")
    published_date: Optional[datetime.datetime] = Field(None, description="The publication date of the entry.")


# --- Response Schema ---
class RssFeedResponse(BaseModel):
    feed_url: HttpUrl = Field(..., description="The original feed URL that was processed.")
    feed_title: Optional[str] = Field(None, description="The title of the feed itself.")
    entries: List[RssEntryItem] = Field([], description="A list of entries extracted from the feed.")
    error_message: Optional[str] = Field(None, description="An error message if processing failed.")