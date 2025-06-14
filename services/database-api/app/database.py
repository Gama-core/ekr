# services/database-api/app/database.py
import logging
import datetime
from typing import Generator, List, Optional

from sqlalchemy import (create_engine, BigInteger, Boolean, Column, DateTime,
                        ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint,
                        String, Table)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session as SQLAlchemySession

# Import from the local config module
from .config import settings

logger = logging.getLogger(__name__)

# --- PSYCOPG2 CHECK (MOVED HERE) ---
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# --- SQLAlchemy ORM Models (MOVED HERE) ---
class Base(DeclarativeBase):
    pass

class Note(Base):
    __tablename__ = 'note'
    # ... (paste the full Note class definition from your schemas.py here)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    version: Mapped[int] = mapped_column(BigInteger)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(255))
    text: Mapped[Optional[str]] = mapped_column(String(4000))
    type_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    creation_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    link_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    color: Mapped[Optional[str]] = mapped_column(String(255))
    __table_args__ = (
        ForeignKeyConstraint(['owner_id'], ['app_user.id'], name='fkjl54w6uv8owox1s3dqb0w4r0y', use_alter=True),
    )
    # The relationship to AppUser is commented out as the AppUser model is not fully included
    # owner: Mapped['AppUser'] = relationship('AppUser', back_populates='note')


# --- Database Engine and Session Setup ---
engine = None
SessionLocal = None

def setup_database_engine():
    global engine, SessionLocal
    if not PSYCOPG2_AVAILABLE:
        logger.error("FATAL: psycopg2 is not installed. This service cannot connect to PostgreSQL.")
        return

    if not all([settings.DB_USER, settings.DB_PASSWORD, settings.DB_HOST, settings.DB_NAME]):
        logger.error("FATAL: Database connection parameters are missing. This service cannot function.")
        return

    try:
        db_url = (
            f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD.get_secret_value()}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        # Test connection
        with engine.connect() as connection:
            logger.info("Database connection test successful.")
    except Exception as e:
        logger.exception("Failed to create SQLAlchemy engine. Service will be non-functional.")
        engine = None
        SessionLocal = None

def get_db() -> Generator[SQLAlchemySession, None, None]:
    if SessionLocal is None:
        logger.error("SessionLocal is not initialized. Cannot provide DB session.")
        # This will raise an error in the endpoint, which is correct behavior.
        raise RuntimeError("Database not connected.")

    db: SQLAlchemySession = SessionLocal()
    try:
        yield db
    finally:
        db.close()