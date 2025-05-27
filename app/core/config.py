import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

logger = logging.getLogger(__name__)


# --- Bootstrap Settings from .env ---
class DbBootstrapSettings(BaseSettings):
    DB_HOST: Optional[str] = Field(None)
    DB_PORT: Optional[str] = Field(None)
    DB_USER: Optional[str] = Field(None)
    DB_PASSWORD: Optional[str] = Field(None, repr=False)
    DB_NAME: Optional[str] = Field(None)
    LOAD_CONFIG_FROM_DB: bool = Field(False)
    ES_HOST: Optional[str] = Field("http://localhost:9200")
    ES_INDEX_NAME: Optional[str] = Field("notes_index")

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)

_db_bootstrap_settings = DbBootstrapSettings()


# --- Load additional settings from database ---
def load_settings_from_db() -> Dict[str, Any]:
    if not (_db_bootstrap_settings.LOAD_CONFIG_FROM_DB and PSYCOPG2_AVAILABLE and
            all([_db_bootstrap_settings.DB_HOST, _db_bootstrap_settings.DB_PORT, _db_bootstrap_settings.DB_USER,
                 _db_bootstrap_settings.DB_NAME])):
        logger.info("Skipping settings load from DB (flag false, psycopg2 missing, or DB params incomplete).")
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
                db_cfg[row['setting_key'].upper()] = row['setting_value']
        logger.info(f"Loaded {len(db_cfg)} settings from DB by core config.")
    except Exception as e:
        logger.error(f"Failed to load settings from DB for core config: {e}", exc_info=True)
        if _db_bootstrap_settings.LOAD_CONFIG_FROM_DB:
            raise SystemExit(f"CRITICAL: DB config load failed for core settings: {e}")
    finally:
        if conn:
            conn.close()
    return db_cfg


# --- Final Settings Object ---
class Settings(BaseSettings):
    # Third-Party API Keys
    GOOGLE_API_KEY: str = Field("core_default_google_api_key", repr=False)
    GOOGLE_CSE_ID: str = Field("core_default_google_cse_id")
    QWEN_API_KEY: str = Field("core_default_qwen_api_key", repr=False)
    QWEN_BASE_URL: str = Field("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus")

    # Core Operational Settings
    UPLOAD_DIR: Path = Field(default_factory=lambda: Path("./uploaded_files_core_default"))

    # Vector Store Configuration (e.g., FAISS)
    VECTOR_STORE_PATH: str = Field("./faiss_data_default")
    EMBEDDING_MODEL_NAME: str = Field("all-MiniLM-L6-v2")
    FAISS_INDEX_FILENAME_DEFAULT: str = Field("faiss_index.idx")

    # Elasticsearch Configuration
    ES_HOST: str = Field("http://localhost:9200")
    ES_INDEX_NAME: str = Field("notes_index")

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        db_loaded_values = load_settings_from_db()
        db_source_callable = lambda: db_loaded_values
        return (init_settings, env_settings, db_source_callable, dotenv_settings, file_secret_settings)

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)


# Global settings instance
settings = Settings()


# --- Ensure Required Directories Exist ---
def ensure_directories_exist():
    try:
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"UPLOAD_DIR ensured at: {upload_dir.resolve()}")

        vector_store_dir = Path(settings.VECTOR_STORE_PATH)
        vector_store_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VECTOR_STORE_PATH (FAISS) ensured at: {vector_store_dir.resolve()}")

        logger.info(f"Elasticsearch host: {settings.ES_HOST}")
        logger.info(f"Elasticsearch index: {settings.ES_INDEX_NAME}")

    except Exception as e:
        logger.error(f"Failed to ensure core directories: {e}", exc_info=True)


ensure_directories_exist()
