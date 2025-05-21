# app/features/web_interaction/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal

# Pydantic models (schemas) for request and response bodies for web interaction features.

# --- Google Search Schemas ---
class GoogleSearchRequest(BaseModel):
    query: str = Field(..., description="The search query.")
    num_results: int = Field(default=5, ge=1, le=10, description="Number of search results (1-10).")

class GoogleSearchResultItem(BaseModel):
    title: Optional[str] = Field(None, description="Title of the search result.")
    link: Optional[HttpUrl] = Field(None, description="URL of the search result.") # Validated as HTTP/HTTPS URL.
    snippet: Optional[str] = Field(None, description="Snippet of the search result.")

class GoogleSearchResponse(BaseModel):
    query_echo: str = Field(..., description="The original query processed.")
    results: List[GoogleSearchResultItem] = Field([], description="List of search results.")
    error_message: Optional[str] = Field(None, description="Error message if search failed.")


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


# --- Search-Then-Crawl Orchestration Schemas ---
class SearchThenCrawlRequest(BaseModel):
    query: str = Field(..., description="The search query.")
    num_search_results_to_crawl: int = Field(default=3, ge=1, le=10, description="Number of top results to crawl.")

class SearchThenCrawlResultItem(CrawlStatus): # Extends CrawlStatus with search-specific info.
    original_search_rank: Optional[int] = Field(None, description="Rank in original search results (1-indexed).")
    url: Optional[HttpUrl] = Field(None, description="The URL attempted to be crawled.")
    search_result_title: Optional[str] = Field(None, description="Title from the search result item.")
    search_result_snippet: Optional[str] = Field(None, description="Snippet from the search result item.")
# Response for SearchThenCrawlRequest is List[SearchThenCrawlResultItem].