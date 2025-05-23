# app/features/google_search/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

# --- Google Search Schemas ---
class GoogleSearchRequest(BaseModel):
    query: str = Field(..., description="The search query.")
    num_results: int = Field(default=5, ge=1, le=10, description="Number of search results (1-10).")

class GoogleSearchResultItem(BaseModel):
    title: Optional[str] = Field(None, description="Title of the search result.")
    link: Optional[HttpUrl] = Field(None, description="URL of the search result.")
    snippet: Optional[str] = Field(None, description="Snippet of the search result.")

class GoogleSearchResponse(BaseModel):
    query_echo: str = Field(..., description="The original query processed.")
    results: List[GoogleSearchResultItem] = Field([], description="List of search results.")
    error_message: Optional[str] = Field(None, description="Error message if search failed.")