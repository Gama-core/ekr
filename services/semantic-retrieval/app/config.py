import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl

class Settings(BaseSettings):
    # --- Service Dependencies ---
    DATABASE_API_URL: HttpUrl = Field("http://localhost:8001", description="URL for the Database API service.")

    # --- Vector Store Configuration ---
    VECTOR_STORE_PATH: Path = Field("./vector_store_data")
    FAISS_INDEX_FILENAME_DEFAULT: str = Field("faiss_index.idx")

    # --- Embedding Model Configuration ---
    # NOTE: In a real-world scenario, you might get these from a central config service
    EMBEDDING_MODEL_PROVIDER: str = Field("huggingface")
    HF_EMBEDDING_MODEL_NAME: str = Field("sentence-transformers/all-MiniLM-L6-v2")
    ACTIVE_EMBEDDING_DIMENSION: int = Field(384)

    # --- LLM Configuration (for LlamaIndex Settings, though not used for generation here) ---
    QWEN_API_KEY: str = Field("your_qwen_api_key")
    QWEN_BASE_URL: str = Field("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus")

    # --- RAG Feature-Specific Settings ---
    DEFAULT_SIMILARITY_TOP_K: int = Field(3)
    DEFAULT_CHUNK_SIZE: int = Field(384)
    DEFAULT_CHUNK_OVERLAP: int = Field(50)
    FORCE_REBUILD_ON_STARTUP: bool = Field(False)
    MAX_NOTES_FOR_INITIAL_BUILD: int = Field(100000)
    INDEX_BATCH_SIZE: int = Field(100)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore',
        case_sensitive=False
    )

settings = Settings()

# Ensure directories exist on startup
settings.VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)