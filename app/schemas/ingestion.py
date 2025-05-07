# app/schemas/ingestion.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any # For the flexible response structure

class IngestionRequest(BaseModel):
    """
    Schema for the request body of the ingestion endpoint.
    """
    query: str = Field(..., description="The search query to use for finding relevant URLs")
    num_results: int = Field(default=5, ge=1, le=10, description="Number of search results to process (Google max is 10 per request)")
    # Add other parameters if needed, e.g., crawl depth, specific domains

class ProcessedUrlResult(BaseModel):
    """
    Schema describing the outcome of processing a single URL.
    """
    url: str
    status: str # e.g., "success", "crawl_failed", "db_error"
    note_id: int | None = None # Use | None for optional fields in Python 3.10+ (or Optional[int])
    document_id: int | None = None
    error: str | None = None

class IngestionResponse(BaseModel):
    """
    Schema for the response body of the ingestion endpoint.
    """
    message: str
    processed_urls: List[ProcessedUrlResult] = []