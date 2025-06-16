import logging
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, model_validator

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Service Dependencies
    DATABASE_API_URL: str = Field("http://localhost:8003")
    LLM_QUERY_API_URL: str = Field("http://localhost:8002")

    # LLM & Embedding Config
    QWEN_API_KEY: Optional[SecretStr] = Field(None, repr=False)
    QWEN_BASE_URL: str = Field("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus")
    EMBEDDING_MODEL_PROVIDER: str = Field("huggingface")
    HF_EMBEDDING_MODEL_NAME: str = Field("sentence-transformers/all-MiniLM-L6-v2")
    HF_EMBEDDING_DIMENSION: int = Field(384)
    ACTIVE_EMBEDDING_DIMENSION: int = Field(384) # Will be set by validator

    # Vector Store Config
    VECTOR_STORE_PATH: Path = Field(default_factory=lambda: Path("./vector_store_data"))
    FAISS_INDEX_FILENAME_DEFAULT: str = Field("faiss_index.idx")

    # Feature Defaults
    DEFAULT_SIMILARITY_TOP_K: int = Field(3)
    DEFAULT_CHUNK_SIZE: int = Field(384)
    DEFAULT_CHUNK_OVERLAP: int = Field(50)
    INDEX_BATCH_SIZE: int = Field(100)
    FORCE_REBUILD_ON_STARTUP: bool = Field(False)
    MAX_NOTES_FOR_INITIAL_BUILD: int = Field(100000)

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)

    @model_validator(mode='after')
    def set_active_embedding_dimension(self) -> 'Settings':
        # This logic can be simplified if only one provider is used, but kept for consistency
        if self.EMBEDDING_MODEL_PROVIDER == "huggingface":
            self.ACTIVE_EMBEDDING_DIMENSION = self.HF_EMBEDDING_DIMENSION
        # Add other providers here if needed
        return self

settings = Settings()
logger.info("Semantic Retrieval Service settings loaded.")