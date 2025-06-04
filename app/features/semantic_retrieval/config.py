# app/features/semantic_retrieval/config.py
from pydantic import BaseModel, Field


class SemanticRetrievalSettings(BaseModel):
    DEFAULT_SIMILARITY_TOP_K: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Default number of top similar documents/chunks to retrieve."
    )

    DEFAULT_CHUNK_SIZE: int = Field(
        default=384,
        description="Default chunk size for LlamaIndex node parsing within this feature."
    )
    DEFAULT_CHUNK_OVERLAP: int = Field(
        default=50,
        description="Default chunk overlap for LlamaIndex node parsing within this feature."
    )

    FORCE_REBUILD_ON_STARTUP: bool = Field(
        default=True,
        description="Force a full rebuild of the vector index on application startup."
    )
    MAX_NOTES_FOR_INITIAL_BUILD: int = Field(
        default=100000,
        description="Maximum number of notes to process during an initial full index build."
    )
    INDEX_BATCH_SIZE: int = Field(
        default=100,
        description="Number of notes to process in a single batch when adding to the index."
    )


semantic_retrieval_config = SemanticRetrievalSettings()