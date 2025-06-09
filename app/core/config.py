# app/core/config.py
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    class RealDictCursor: pass # To satisfy linters if psycopg2 is missing

logger = logging.getLogger(__name__)


# --- Bootstrap Settings from .env ---
class DbBootstrapSettings(BaseSettings):
    """
    Settings loaded initially from .env to bootstrap DB connection
    for loading further application settings. Also includes core
    Elasticsearch settings that must come from the environment.
    """
    # Database Settings
    DB_HOST: Optional[str] = Field(None)
    DB_PORT: Optional[str] = Field(None)
    DB_USER: Optional[str] = Field(None)
    DB_PASSWORD: Optional[str] = Field(None, repr=False)
    DB_NAME: Optional[str] = Field(None)
    LOAD_CONFIG_FROM_DB: bool = Field(False)

    # --- Elasticsearch Core Settings (to be loaded from .env) ---
    ES_HOST: Optional[str] = Field("http://localhost:9200") # Default, can be overridden
    ES_INDEX_NAME: Optional[str] = Field("notes_index")

    # For Elastic Cloud connection
    ES_CLOUD_ID: Optional[str] = Field(None)
    ES_API_KEY_ID: Optional[str] = Field(None)
    ES_API_KEY: Optional[str] = Field(None, repr=False) # repr=False for secrets

    # For basic auth (generic or AWS OpenSearch with basic auth)
    ES_USERNAME: Optional[str] = Field(None)
    ES_PASSWORD: Optional[str] = Field(None, repr=False) # repr=False for secrets

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)

_db_bootstrap_settings = DbBootstrapSettings()


# --- Load additional settings from database ---
def load_settings_from_db_func() -> Dict[str, Any]:
    """
    Loads settings from the 'application_settings' table in PostgreSQL.
    Uses DbBootstrapSettings for connection parameters.
    """
    if not (_db_bootstrap_settings.LOAD_CONFIG_FROM_DB and PSYCOPG2_AVAILABLE and
            all([_db_bootstrap_settings.DB_HOST, _db_bootstrap_settings.DB_PORT,
                 _db_bootstrap_settings.DB_USER, _db_bootstrap_settings.DB_NAME])):
        if not _db_bootstrap_settings.LOAD_CONFIG_FROM_DB:
            logger.info("LOAD_CONFIG_FROM_DB is False. Skipping settings load from DB.")
        else:
            logger.warning(
                "Skipping settings load from DB: psycopg2 missing or DB connection parameters incomplete in DbBootstrapSettings."
            )
        return {}

    db_cfg: Dict[str, Any] = {}
    conn = None
    try:
        conn_params = {
            "host": _db_bootstrap_settings.DB_HOST,
            "port": _db_bootstrap_settings.DB_PORT,
            "user": _db_bootstrap_settings.DB_USER,
            "dbname": _db_bootstrap_settings.DB_NAME
        }
        if _db_bootstrap_settings.DB_PASSWORD:
            conn_params["password"] = _db_bootstrap_settings.DB_PASSWORD

        conn = psycopg2.connect(**conn_params)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT setting_key, setting_value FROM public.application_settings"
            cur.execute(query)
            for row in cur.fetchall():
                db_cfg[str(row['setting_key']).upper()] = row['setting_value']
        logger.info(f"Successfully loaded {len(db_cfg)} settings from database (application_settings table).")
    except Exception as e:
        logger.error(f"Failed to load settings from database: {type(e).__name__} - {e}", exc_info=True)
        if _db_bootstrap_settings.LOAD_CONFIG_FROM_DB:
            raise SystemExit(f"CRITICAL: Database configuration load failed: {e}")
    finally:
        if conn:
            conn.close()
    return db_cfg


# --- Final Settings Object ---
class Settings(BaseSettings):
    """
    Main application settings.
    """
    # --- Mistral AI API Settings (for OCR) ---
    MISTRAL_API_KEY: str = Field("core_default_mistral_api_key_placeholder", repr=False)
    MISTRAL_API_BASE_URL: str = Field("https://api.mistral.ai", description="Base URL for Mistral AI APIs.")
    MISTRAL_OCR_DEFAULT_MODEL: str = Field("mistral-ocr-latest", description="Default Mistral model for OCR.")

    # --- Third-Party API Keys ---
    GOOGLE_API_KEY: str = Field("core_default_google_api_key_placeholder", repr=False)
    GOOGLE_CSE_ID: str = Field("core_default_google_cse_id_placeholder")
    QWEN_API_KEY: str = Field("core_default_dashscope_api_key_placeholder", repr=False)
    QWEN_BASE_URL: str = Field("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus", description="Default Qwen model for LLM chat interactions.")

    # Core Operational Settings
    UPLOAD_DIR: Path = Field(default_factory=lambda: Path("./uploaded_files_core_default"))

    # --- Elasticsearch Configuration (Sourced from DbBootstrapSettings) ---
    ES_HOST: Optional[str] = Field(default_factory=lambda: _db_bootstrap_settings.ES_HOST)
    ES_INDEX_NAME: str = Field(default_factory=lambda: _db_bootstrap_settings.ES_INDEX_NAME or "notes_index")
    ES_CLOUD_ID: Optional[str] = Field(default_factory=lambda: _db_bootstrap_settings.ES_CLOUD_ID)
    ES_API_KEY_ID: Optional[str] = Field(default_factory=lambda: _db_bootstrap_settings.ES_API_KEY_ID)
    ES_API_KEY: Optional[str] = Field(default_factory=lambda: _db_bootstrap_settings.ES_API_KEY, repr=False)
    ES_USERNAME: Optional[str] = Field(default_factory=lambda: _db_bootstrap_settings.ES_USERNAME)
    ES_PASSWORD: Optional[str] = Field(default_factory=lambda: _db_bootstrap_settings.ES_PASSWORD, repr=False)

    # --- Vector Store Configuration ---
    VECTOR_STORE_PATH: Path = Field(default_factory=lambda: Path("./vector_store_data"),
                                    description="Base directory for storing FAISS index files and related metadata.")
    FAISS_INDEX_FILENAME_DEFAULT: str = Field("faiss_index.idx",
                                              description="Default filename for the FAISS persisted index file.")

    # --- Embedding Model Configuration ---
    EMBEDDING_MODEL_PROVIDER: str = Field("huggingface",
                                          description="Provider for the embedding model ('huggingface' or 'dashscope')")

    # HuggingFace specific
    HF_EMBEDDING_MODEL_NAME: str = Field("sentence-transformers/all-MiniLM-L6-v2",
                                         description="HuggingFace model name for embeddings.")
    HF_EMBEDDING_DIMENSION: int = Field(384, description="Dimension for the HuggingFace embedding model.")

    # DashScope specific
    DASHSCOPE_EMBEDDING_MODEL_NAME: Optional[str] = Field("text-embedding-v3", description="DashScope embedding model.")
    DASHSCOPE_EMBEDDING_DIMENSIONS: Optional[int] = Field(1024,
                                                          description="Dimension for DashScope model (1024, 768, or 512).")

    # This will be set by the validator based on the provider
    ACTIVE_EMBEDDING_DIMENSION: int = Field(384,
                                            description="Currently active embedding dimension based on provider.")

    @model_validator(mode='after')
    def set_active_embedding_dimension(self) -> 'Settings':
        if self.EMBEDDING_MODEL_PROVIDER == "huggingface":
            self.ACTIVE_EMBEDDING_DIMENSION = self.HF_EMBEDDING_DIMENSION
            logger.info(f"Active embedding provider set to HuggingFace. Dimension: {self.ACTIVE_EMBEDDING_DIMENSION}")
        elif self.EMBEDDING_MODEL_PROVIDER == "dashscope":
            if self.DASHSCOPE_EMBEDDING_DIMENSIONS is None:
                logger.error("DashScope is provider, but DASHSCOPE_EMBEDDING_DIMENSIONS is not set.")
                self.ACTIVE_EMBEDDING_DIMENSION = 1024
            else:
                self.ACTIVE_EMBEDDING_DIMENSION = self.DASHSCOPE_EMBEDDING_DIMENSIONS
            logger.info(f"Active embedding provider set to DashScope. Dimension: {self.ACTIVE_EMBEDDING_DIMENSION}")
        else:
            logger.warning(
                f"Unknown EMBEDDING_MODEL_PROVIDER: '{self.EMBEDDING_MODEL_PROVIDER}'. "
                f"Defaulting ACTIVE_EMBEDDING_DIMENSION to HF dimension: {self.HF_EMBEDDING_DIMENSION}."
            )
            self.ACTIVE_EMBEDDING_DIMENSION = self.HF_EMBEDDING_DIMENSION

        allowed_dims = [1024, 768, 512, 384, 1536] # Common dimensions
        if self.ACTIVE_EMBEDDING_DIMENSION not in allowed_dims:
            logger.warning(
                f"ACTIVE_EMBEDDING_DIMENSION dynamically set to {self.ACTIVE_EMBEDDING_DIMENSION}, "
                f"which is not in the common list {allowed_dims}. "
                "Ensure this is correct for your chosen model."
            )
        return self

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
    ):
        db_settings_provider = load_settings_from_db_func
        return (
            init_settings,
            dotenv_settings,
            db_settings_provider,
            env_settings,
            file_secret_settings,
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore',
        case_sensitive=False
    )

# Create the settings instance
settings = Settings()


# Standalone function to ensure directories exist
def ensure_directories_exist():
    """Ensures that necessary directories defined in settings exist."""
    try:
        upload_dir = settings.UPLOAD_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"UPLOAD_DIR ensured at: {upload_dir.resolve()}")

        vector_store_dir = settings.VECTOR_STORE_PATH
        vector_store_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VECTOR_STORE_PATH (for FAISS) ensured at: {vector_store_dir.resolve()}")

        # Log Elasticsearch connection info (be careful not to log secrets)
        if settings.ES_CLOUD_ID:
            logger.info(f"Elasticsearch configured with Cloud ID: {settings.ES_CLOUD_ID[:15]}...") # Log prefix
            logger.info(f"Elasticsearch API Key ID: {settings.ES_API_KEY_ID}")
        elif settings.ES_HOST:
            logger.info(f"Elasticsearch host: {settings.ES_HOST}")
            if settings.ES_USERNAME:
                logger.info(f"Elasticsearch username: {settings.ES_USERNAME}")
        else:
            logger.warning("Elasticsearch connection details (Cloud ID or Host) not found in settings.")
        logger.info(f"Elasticsearch index: {settings.ES_INDEX_NAME}")

    except Exception as e:
        logger.error(f"Failed to ensure core directories exist: {e}", exc_info=True)
        # Depending on criticality, you might want to raise SystemExit here


# Logging after settings instance is fully resolved
logger.info(f"Application settings loaded. LOAD_CONFIG_FROM_DB is '{_db_bootstrap_settings.LOAD_CONFIG_FROM_DB}'.")

# Log active embedding configuration
logger.info(
    f"EMBEDDING_MODEL_PROVIDER: '{settings.EMBEDDING_MODEL_PROVIDER}'. "
    f"Active embedding dimension: {settings.ACTIVE_EMBEDDING_DIMENSION}."
)
if settings.EMBEDDING_MODEL_PROVIDER == "huggingface":
    logger.info(f"  HuggingFace Model: '{settings.HF_EMBEDDING_MODEL_NAME}'.")
elif settings.EMBEDDING_MODEL_PROVIDER == "dashscope" and settings.DASHSCOPE_EMBEDDING_MODEL_NAME:
    logger.info(f"  DashScope Model: '{settings.DASHSCOPE_EMBEDDING_MODEL_NAME}'.")

logger.info(f"Vector store path: '{settings.VECTOR_STORE_PATH.resolve()}'")

# Call ensure_directories_exist at the end of the module to prepare paths
ensure_directories_exist()