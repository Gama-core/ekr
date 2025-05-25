# app/core/database.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from typing import Generator

# Use _db_bootstrap_settings for initial DB connection parameters
from app.core.config import _db_bootstrap_settings, PSYCOPG2_AVAILABLE, settings # Import settings for other uses if any

logger = logging.getLogger(__name__)

if not PSYCOPG2_AVAILABLE:
    logger.error("psycopg2 is not installed. PostgreSQL connectivity will not be available.")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./temp_placeholder.db" # Fallback
else:
    # Use _db_bootstrap_settings here
    if (_db_bootstrap_settings.DB_USER and
            _db_bootstrap_settings.DB_PASSWORD and
            _db_bootstrap_settings.DB_HOST and
            _db_bootstrap_settings.DB_NAME):
        SQLALCHEMY_DATABASE_URL = (
            f"postgresql+psycopg2://{_db_bootstrap_settings.DB_USER}:{_db_bootstrap_settings.DB_PASSWORD}"
            f"@{_db_bootstrap_settings.DB_HOST}:{_db_bootstrap_settings.DB_PORT or 5432}/{_db_bootstrap_settings.DB_NAME}"
        )
        logger.info(
            f"Database URL configured for PostgreSQL: "
            f"postgresql+psycopg2://{_db_bootstrap_settings.DB_USER}:****"
            f"@{_db_bootstrap_settings.DB_HOST}:{_db_bootstrap_settings.DB_PORT or 5432}/{_db_bootstrap_settings.DB_NAME}"
        )
    else:
        logger.warning(
            "One or more PostgreSQL connection parameters (DB_USER, DB_PASSWORD, DB_HOST, DB_NAME) "
            "are missing from DbBootstrapSettings (likely .env). "
            "Database connectivity for Notes will be impaired."
        )
        SQLALCHEMY_DATABASE_URL = "sqlite:///./temp_fallback_db.db"


try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("SQLAlchemy engine and SessionLocal created.")
except Exception as e:
    logger.exception(f"Failed to create SQLAlchemy engine or SessionLocal with URL {SQLALCHEMY_DATABASE_URL}")
    engine = None # type: ignore
    SessionLocal = None # type: ignore


def get_db() -> Generator[SQLAlchemySession, None, None]:
    if SessionLocal is None:
        logger.error("SessionLocal is not initialized. Cannot provide DB session.")
        raise RuntimeError("Database session factory (SessionLocal) is not initialized.")

    db: SQLAlchemySession = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    if not PSYCOPG2_AVAILABLE or engine is None:
        logger.warning("Cannot check DB connection: psycopg2 not available or engine not initialized.")
        return False
    try:
        with engine.connect() as connection:
            logger.info("Successfully connected to the database via SQLAlchemy engine.")
            return True
    except Exception as e:
        logger.error(f"Failed to connect to the database via SQLAlchemy engine: {e}", exc_info=True)
        return False