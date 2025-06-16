import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- DTO (Data Transfer Object) from database-api ---
class NoteForIndex(BaseModel):
    id: int
    title: str
    text_content: Optional[str] = Field(None, alias='text')
    owner_id: int
    creation_date: Optional[datetime.datetime]

    class Config:
        from_attributes = True
        populate_by_name = True

# --- API Request Schemas (for this service's own endpoints) ---
class IndexNoteByIdRequest(BaseModel):
    note_id: int

class RetrieveRequest(BaseModel):
    query: str
    user_id: int
    top_k: Optional[int] = None

# --- API Response Schemas (for this service's own endpoints) ---
class IndexOperationResponse(BaseModel):
    status: str
    note_id: Optional[int] = None
    doc_id: Optional[str] = None
    message: str

class RetrievedContextItem(BaseModel):
    note_id: Optional[int] = None
    doc_id: Optional[str] = None
    title: Optional[str] = None
    text_chunk: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class RetrieveResponse(BaseModel):
    query_echo: str
    user_id_echo: int
    retrieved_items: List[RetrievedContextItem]
    message: Optional[str] = None

class IndexStatsResponse(BaseModel):
    total_indexed_vectors: int
    num_docs_in_docstore: Optional[int] = None
    faiss_index_type: Optional[str] = None
    faiss_index_dimension: Optional[int] = None
    llama_configured_chunk_size: Optional[int] = None
    llama_configured_chunk_overlap: Optional[int] = None
    llama_embedding_model_name: Optional[str] = None
    index_storage_path: Optional[str] = None
    message: str

class RebuildStatusResponse(BaseModel):
    status: str
    message: str