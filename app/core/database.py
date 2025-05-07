# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings # Import the settings instance

# Create the SQLAlchemy engine using the URL from settings
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False} # Only needed for SQLite
    pool_pre_ping=True # Good practice for handling connections
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for declarative models
Base = declarative_base()

# Dependency to get DB session for API endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()