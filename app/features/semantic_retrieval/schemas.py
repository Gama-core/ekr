# app/features/semantic_retrieval/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import datetime

from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema


# --- API Request Schemas ---

class IndexNoteByIdRequest(BaseModel):
    note_id: int = Field(..., description="The ID of the note (from PostgreSQL) to fetch and index.")


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's query string for semantic retrieval.")
    user_id: int = Field(..., description="The ID of the user performing the query, for data filtering.")
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of top similar results to retrieve."
    )

# --- API Response Schemas ---

class IndexOperationResponse(BaseModel):
    status: str = Field(..., description="Status of the indexing operation (e.g., 'success', 'failed', 'not_found').")
    note_id: Optional[int] = Field(None, description="The ID of the note processed.")
    doc_id: Optional[str] = Field(None, description="The internal document ID used in the vector index (e.g., 'note_X').")
    message: str = Field(..., description="A descriptive message about the operation.")

class RetrievedContextItem(BaseModel):
    note_id: Optional[int] = Field(None, description="The ID of the original note.")
    doc_id: Optional[str] = Field(None, description="The LlamaIndex document ID (e.g., 'note_X').")
    title: Optional[str] = Field(None, description="Title of the source note.")
    text_chunk: str = Field(..., description="The retrieved chunk of text.")
    score: Optional[float] = Field(None, description="Relevance score of the retrieved chunk (higher is better).")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata from the indexed node.")

class RetrieveResponse(BaseModel):
    query_echo: str = Field(..., description="The original query string that was processed.")
    user_id_echo: int = Field(..., description="The user_id for whom the query was processed.")
    retrieved_items: List[RetrievedContextItem] = Field([], description="List of retrieved context items.")
    message: Optional[str] = Field(None, description="Optional message, e.g., if no items found or an error occurred.")

class IndexStatsResponse(BaseModel):
    total_indexed_vectors: int = Field(..., description="Total number of vectors (chunks) currently in the FAISS index.")
    message: str = Field("Index statistics retrieved successfully.", description="Status message.")

class RebuildStatusResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[int] = Field(None, description="User ID if rebuild was user-specific.") # Kept for potential future use
    notes_processed: Optional[int] = None
    vectors_added: Optional[int] = None