import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.endpoints import router as api_router

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("--- RSS Extractor Service Starting Up ---")
    yield
    # Shutdown
    logger.info("--- RSS Extractor Service Shutting Down ---")

app = FastAPI(
    title="RSS Extractor Service",
    description="A microservice for parsing RSS and Atom feeds.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Checks if the service is running."""
    return {"status": "OK"}

# Include all API endpoints from the router
app.include_router(api_router)