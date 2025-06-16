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
    score: Optional[float] = Field(None, description="Relevance score (FAISS distance) of the retrieved chunk — lower means more similar.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata from the indexed node.")

class RetrieveResponse(BaseModel):
    query_echo: str = Field(..., description="The original query string that was processed.")
    user_id_echo: int = Field(..., description="The user_id for whom the query was processed.")
    retrieved_items: List[RetrievedContextItem] = Field([], description="List of retrieved context items.")
    message: Optional[str] = Field(None, description="Optional message, e.g., if no items found or an error occurred.")


class IndexStatsResponse(BaseModel):
    total_indexed_vectors: int = Field(...,
                                       description="Total number of vectors (chunks) currently in the FAISS index.")
    num_docs_in_docstore: Optional[int] = Field(None,
                                                description="Total number of source documents in the LlamaIndex DocStore.")

    faiss_index_type: Optional[str] = Field(None, description="Type of the underlying FAISS index (e.g., IndexFlatL2).")
    faiss_index_dimension: Optional[int] = Field(None, description="Dimension of the vectors in the FAISS index.")

    llama_configured_chunk_size: Optional[int] = Field(None,
                                                       description="Chunk size configured in LlamaIndex Settings.")
    llama_configured_chunk_overlap: Optional[int] = Field(None,
                                                          description="Chunk overlap configured in LlamaIndex Settings.")
    llama_embedding_model_name: Optional[str] = Field(None,
                                                      description="Embedding model name from LlamaIndex Settings.")
    index_storage_path: Optional[str] = Field(None, description="File system path to the index storage directory.")
    message: str = Field("Index statistics retrieved successfully.", description="Overall status message.")


class RebuildStatusResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[int] = Field(None, description="User ID if rebuild was user-specific.")  # Kept for potential future use
    notes_processed: Optional[int] = None
    vectors_added: Optional[int] = None
