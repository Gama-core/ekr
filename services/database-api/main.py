# services/database-api/main.py
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
import uvicorn # --- NEW: Import uvicorn ---

# Import from the app package
from app.endpoints import router as api_router
from app.database import setup_database_engine, engine, get_db
from app.config import settings # --- NEW: Import settings ---

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# --- FastAPI Lifespan and App Creation ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("--- Database API Service Starting Up ---")
    setup_database_engine()
    yield
    # Shutdown
    logger.info("--- Database API Service Shutting Down ---")

app = FastAPI(
    title="Database API Service",
    description="Provides API access to application's note data.",
    version="1.3.0", # Bumped version for new features
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Checks if the service is running and connected to the database."""
    if engine is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection is not available.")
    try:
        # A lightweight check
        with engine.connect() as connection:
            pass
        return {"status": "OK", "database_connection": "successful"}
    except Exception as e:
        logger.error(f"Health check failed to connect to database: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed.")

# Include all API endpoints from the router
app.include_router(api_router)

# --- NEW: Block to make main.py executable ---
if __name__ == "__main__":
    logger.info(f"Starting Database API Service on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True
    )