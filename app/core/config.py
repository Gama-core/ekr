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


def load_settings_from_db() -> Dict[str, Any]:  # Renamed back to generic
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
            # Or, be more specific if your table has many unrelated settings.
            query = "SELECT setting_key, setting_value FROM public.application_settings"
            # Example of more specific query if needed:
            # query = ("SELECT setting_key, setting_value FROM public.application_settings WHERE "
            #          "UPPER(setting_key) LIKE 'QWEN_%' OR "
            #          "UPPER(setting_key) LIKE 'UPLOAD_%' OR "
            #          "UPPER(setting_key) LIKE 'VECTOR_%' OR "
            #          "UPPER(setting_key) LIKE 'DEFAULT_CHROMA_%' OR "
            #          "UPPER(setting_key) LIKE 'EMBEDDING_%' OR "
            #          "UPPER(setting_key) = 'GOOGLE_API_KEY' OR " # Exact match for these
            #          "UPPER(setting_key) = 'GOOGLE_CSE_ID'")
            cur.execute(query)  # Using simple "fetch all" for now
            for row in cur.fetchall():
                db_cfg[row['setting_key'].upper()] = row['setting_value']
        logger.info(f"Loaded {len(db_cfg)} settings from DB by core config.")
    except Exception as e:
        logger.error(f"Failed to load settings from DB for core config: {e}", exc_info=True)
        if _db_bootstrap_settings.LOAD_CONFIG_FROM_DB:
            raise SystemExit(f"CRITICAL: DB config load failed for core settings: {e}")
    finally:
        if conn: conn.close()
    return db_cfg


class Settings(BaseSettings):
    # --- Third-Party API Keys (now all potentially loaded from DB by core) ---
    GOOGLE_API_KEY: str = Field("core_default_google_api_key", repr=False)
    GOOGLE_CSE_ID: str = Field("core_default_google_cse_id")
    QWEN_API_KEY: str = Field("core_default_qwen_api_key", repr=False)
    QWEN_BASE_URL: str = Field("https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    QWEN_DEFAULT_MODEL: str = Field("qwen-plus")

    # --- Core Operational Settings ---
    UPLOAD_DIR: Path = Field(default_factory=lambda: Path("./uploaded_files_core_default"))
    VECTOR_STORE_PATH: str = Field("./chroma_db_core_default")
    EMBEDDING_MODEL_NAME: str = Field("all-MiniLM-L6-v2")
    DEFAULT_CHROMA_COLLECTION_NAME: str = Field("core_knowledge_collection_default")

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings,
                                   file_secret_settings):
        db_loaded_values = load_settings_from_db()

        # logger.info(f"DEBUG core: init_settings type={type(init_settings)}, callable={callable(init_settings)}")
        # logger.info(f"DEBUG core: env_settings type={type(env_settings)}, callable={callable(env_settings)}")
        # logger.info(f"DEBUG core: db_loaded_values type={type(db_loaded_values)}, callable={callable(db_loaded_values)}")
        # logger.info(f"DEBUG core: dotenv_settings type={type(dotenv_settings)}, callable={callable(dotenv_settings)}")
        # logger.info(f"DEBUG core: file_secret_settings type={type(file_secret_settings)}, callable={callable(file_secret_settings)}")

        db_source_callable = lambda: db_loaded_values  # Wrap dict in a callable

        return (init_settings, env_settings, db_source_callable, dotenv_settings, file_secret_settings)

    model_config = SettingsConfigDict(env_file=".env", extra='ignore', case_sensitive=False)


settings = Settings()  # Global core settings instance.


def ensure_directories_exist():
    try:
        upload_dir_value = settings.UPLOAD_DIR
        upload_dir = Path(upload_dir_value) if isinstance(upload_dir_value, str) else upload_dir_value
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Core UPLOAD_DIR ensured at: {upload_dir.resolve()}")
        logger.info(f"Core VECTOR_STORE_PATH configured to: {Path(settings.VECTOR_STORE_PATH).resolve()}")
    except Exception as e:
        logger.error(f"Failed to ensure core directories: {e}", exc_info=True)


ensure_directories_exist()