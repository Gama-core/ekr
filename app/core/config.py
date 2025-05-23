# app/core/config.py
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
    # class RealDictCursor: pass # type: ignore

logger = logging.getLogger(__name__)


class DbBootstrapSettings(BaseSettings):
    DB_HOST: Optional[str] = Field(None)
    DB_PORT: Optional[str] = Field(None)
    DB_USER: Optional[str] = Field(None)
    DB_PASSWORD: Optional[str] = Field(None, repr=False)
    DB_NAME: Optional[str] = Field(None)
    LOAD_CONFIG_FROM_DB: bool = Field(False)
    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)


_db_bootstrap_settings = DbBootstrapSettings()


def load_settings_from_db() -> Dict[str, Any]:
    if not (_db_bootstrap_settings.LOAD_CONFIG_FROM_DB and PSYCOPG2_AVAILABLE and
            all([_db_bootstrap_settings.DB_HOST, _db_bootstrap_settings.DB_PORT, _db_bootstrap_settings.DB_USER,
                 _db_bootstrap_settings.DB_NAME])):
        logger.info("Skipping settings load from DB (flag false, psycopg2 missing, or DB params incomplete).")
        return {}

    db_cfg: Dict[str, Any] = {}
    conn = None
    try:
        conn_params = {"host": _db_bootstrap_settings.DB_HOST, "port": _db_bootstrap_settings.DB_PORT,
                       "user": _db_bootstrap_settings.DB_USER, "dbname": _db_bootstrap_settings.DB_NAME}
        if _db_bootstrap_settings.DB_PASSWORD: conn_params["password"] = _db_bootstrap_settings.DB_PASSWORD

        conn = psycopg2.connect(**conn_params)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Fetch all settings; Pydantic fields will pick what they need.
            query = "SELECT setting_key, setting_value FROM public.application_settings"
            cur.execute(query)
            for row in cur.fetchall():
                db_cfg[row['setting_key'].upper()] = row['setting_value'] # Ensure keys are uppercase
        logger.info(f"Loaded {len(db_cfg)} settings from DB by core config.")
    except Exception as e:
        logger.error(f"Failed to load settings from DB for core config: {e}", exc_info=True)
        if _db_bootstrap_settings.LOAD_CONFIG_FROM_DB:
            raise SystemExit(f"CRITICAL: DB config load failed for core settings: {e}")
    finally:
        if conn: conn.close()
    return db_cfg


class Settings(BaseSettings):
    # --- Third-Party API Keys ---
    GOOGLE_API_KEY: str = Field("core_default_google_api_key", repr=False)
    GOOGLE_CSE_ID: str = Field("core_default_google_cse_id")
    QWEN_API_KEY: str = Field("core_default_qwen_api_key", repr=False)
    QWEN_BASE_URL: str = Field("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus")

    # --- Core Operational Settings ---
    UPLOAD_DIR: Path = Field(default_factory=lambda: Path("./uploaded_files_core_default"))

    # --- Vector Store Configuration (FAISS) ---
    VECTOR_STORE_PATH: str = Field("./faiss_data_default", description="Directory for storing FAISS index files and metadata.")
    EMBEDDING_MODEL_NAME: str = Field("all-MiniLM-L6-v2", description="Sentence Transformers embedding model name.")

    FAISS_INDEX_FILENAME_DEFAULT: str = Field("faiss_index.idx", description="Default filename for the FAISS index.")
    # You might also want a setting for a FAISS metadata file, e.g.:
    # FAISS_METADATA_FILENAME_DEFAULT: str = Field("faiss_metadata.json", description="Default filename for FAISS metadata store.")


    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings,
                                   file_secret_settings):
        db_loaded_values = load_settings_from_db()
        db_source_callable = lambda: db_loaded_values

        return (init_settings, env_settings, db_source_callable, dotenv_settings, file_secret_settings)

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)


settings = Settings()


def ensure_directories_exist():
    try:
        upload_dir_value = settings.UPLOAD_DIR
        upload_dir = Path(upload_dir_value) if isinstance(upload_dir_value, str) else upload_dir_value
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Core UPLOAD_DIR ensured at: {upload_dir.resolve()}")

        # Ensure the directory for FAISS index exists
        vector_store_dir_value = settings.VECTOR_STORE_PATH
        vector_store_dir = Path(vector_store_dir_value) if isinstance(vector_store_dir_value, str) else Path(vector_store_dir_value)
        vector_store_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Core VECTOR_STORE_PATH (for FAISS) ensured at: {vector_store_dir.resolve()}")

    except Exception as e:
        logger.error(f"Failed to ensure core directories: {e}", exc_info=True)

ensure_directories_exist()