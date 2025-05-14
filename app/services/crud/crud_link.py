# app/schemas/ingestion.py

from pydantic import BaseModel, Field, HttpUrl # Added HttpUrl
from typing import List, Optional # Ensured Optional is imported

# --- Existing Schemas (with minor adjustment to ProcessedUrlResult) ---
class IngestionRequest(BaseModel):
    """
    Schema for the request body of the /search-and-crawl ingestion endpoint.
    """
    query: str = Field(..., description="The search query to use for finding relevant URLs")
    num_results: int = Field(default=5, ge=1, le=10, description="Number of search results to process (Google max is 10 per request)")

class ProcessedUrlResult(BaseModel):
    """
    Schema describing the outcome of processing a single URL,
    or the result of a single item ingestion (like text or file).
    """
    # Make url optional because text/file ingestion might not have a primary source URL
    url: Optional[str] = Field(None, description="The URL processed, if applicable.")
    status: str = Field(..., description="Status of the processing (e.g., 'success', 'crawl_failed', 'db_error').")
    note_id: Optional[int] = Field(None, description="ID of the created Note, if successful.")
    document_id: Optional[int] = Field(None, description="ID of the created Document, if successful and applicable.")
    error: Optional[str] = Field(None, description="Error message if processing failed.")
    message: Optional[str] = Field(None, description="Additional message providing context about the processing.") # Added for more detail

class IngestionResponse(BaseModel):
    """
    Schema for the response body of the multi-URL /search-and-crawl ingestion endpoint.
    """
    message: str
    processed_urls: List[ProcessedUrlResult] = []


# --- NEW SCHEMAS for /ingest/url and /ingest/text ---

class IngestUrlRequest(BaseModel):
    """
    Request schema for ingesting content from a single URL.
    """
    url: HttpUrl = Field(..., description="The URL to crawl and ingest.")
    parent_note_id: Optional[int] = Field(None, description="Optional ID of an existing Note to set as the parent for the newly created Note.")
    # You could add more fields here if needed, e.g.:
    # custom_doc_type_id: Optional[int] = None
    # custom_note_type_id: Optional[int] = None

    model_config = { # Pydantic v2 example
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://blog.example.com/my-latest-article",
                    "parent_note_id": 105
                }
            ]
        }
    }

class IngestTextRequest(BaseModel):
    """
    Request schema for ingesting raw text content.
    """
    title: str = Field(..., min_length=1, max_length=255, description="Title for the new Note created from the text.")
    text_content: str = Field(..., min_length=1, description="The raw text content to be ingested into a new Note.")
    parent_note_id: Optional[int] = Field(None, description="Optional ID of an existing Note to set as the parent for the newly created Note.")
    # You could add more fields here if needed, e.g.:
    # custom_note_type_id: Optional[int] = None
    # color: Optional[str] = None

    model_config = { # Pydantic v2 example
        "json_schema_extra": {
            "examples": [
                {
                    "title": "My Quick Thoughts on Topic X",
                    "text_content": "This is a short piece of text I want to save as a note...",
                    "parent_note_id": 201
                }
            ]
        }
    }

# --- NEW RESPONSE SCHEMA for single item ingestion (URL, Text, File) ---

class SingleIngestionResult(BaseModel):
    """
    Schema for the response of single-item ingestion endpoints (/url, /text, /file).
    This provides a consistent structure.
    """
    message: str = Field(..., description="A summary message about the ingestion outcome.")
    note_id: Optional[int] = Field(None, description="ID of the created Note, if successful.")
    document_id: Optional[int] = Field(None, description="ID of the created Document, if successful and applicable (e.g., for URL or File ingestion).")
    error: Optional[str] = Field(None, description="Error message if the ingestion failed.")
    # Optional: include the processed item identifier for clarity, like the URL or filename
    identifier_processed: Optional[str] = Field(None, description="The identifier of the item processed (e.g., URL, filename).")

    model_config = { # Pydantic v2 example
        "json_schema_extra": {
            "examples": [
                {
                    "message": "URL ingested successfully.",
                    "note_id": 301,
                    "document_id": 55,
                    "identifier_processed": "https://example.com/article"
                },
                {
                    "message": "Text ingested successfully as a new note.",
                    "note_id": 302,
                    "identifier_processed": "My Quick Thoughts on Topic X" # Could be the title for text
                },
                {
                    "message": "Failed to crawl URL: Timeout.",
                    "error": "Crawl timed out (60s)",
                    "identifier_processed": "https://very-slow-website.com"
                }
            ]
        }
    }

# For the /ingest/file endpoint, the request data (like parent_note_id, doc_type_id)
# will come from FastAPI's `Form` fields, and the file itself via `UploadFile`.
# So, no specific Pydantic *request body* model is typically needed for the entire /file request,
# unless you wanted to group all form fields into a Pydantic model that the endpoint
# then receives as a dependency. For now, using individual Form fields in the endpoint is fine.