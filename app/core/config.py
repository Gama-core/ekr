# app/core/config.py
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict # For loading settings.
from pydantic import Field # For field descriptions.

# Defines application-wide configuration settings.
class Settings(BaseSettings):
    # --- Third-Party API Keys ---
    GOOGLE_API_KEY: str = Field(..., description="API key for Google Custom Search.")
    GOOGLE_CSE_ID: str = Field(..., description="Custom Search Engine ID for Google.")
    QWEN_API_KEY: str = Field(..., description="API key for Qwen LLM.")
    QWEN_BASE_URL: str = Field(..., description="Base URL for Qwen LLM API.")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus", description="Default Qwen model.")

    # --- Operational Settings ---
    UPLOAD_DIR: Path = Field(
        default_factory=lambda: Path("./uploaded_files_feature_store"),
        description="Directory for storing uploaded files."
    )

    # --- Vector Store Configuration ---
    VECTOR_STORE_PATH: str = Field("./chroma_db_store", description="Path for ChromaDB persistence.")
    EMBEDDING_MODEL_NAME: str = Field("all-MiniLM-L6-v2", description="Sentence Transformers embedding model.")
    DEFAULT_CHROMA_COLLECTION_NAME: str = Field("knowledge_collection", description="Default ChromaDB collection name.")

    # Pydantic model configuration for loading from .env file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

# Global instance of application settings.
settings = Settings()

# Ensures necessary directories exist on application startup.
def ensure_directories_exist():
    try:
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # ChromaDB usually handles its own directory creation for VECTOR_STORE_PATH.
    except Exception as e:
        import logging # Local import for this function.
        logger = logging.getLogger(__name__)
        logger.error(f"CRITICAL: Failed to create necessary directories: {e}", exc_info=True)

ensure_directories_exist()