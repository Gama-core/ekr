import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.endpoints import router as api_router
from app.config import settings

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("--- Google Search Service Starting Up ---")
    if not all([settings.GOOGLE_API_KEY, settings.GOOGLE_CSE_ID]):
        logger.warning("Service is starting in a degraded state. API calls will fail until configured.")
    yield
    # Shutdown
    logger.info("--- Google Search Service Shutting Down ---")

app = FastAPI(
    title="Google Search Service",
    description="A microservice for performing Google Custom Searches.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Checks if the service is running and configured."""
    if not all([settings.GOOGLE_API_KEY, settings.GOOGLE_CSE_ID]):
        return {"status": "degraded", "detail": "Google API credentials are not configured."}
    return {"status": "OK"}

# Include all API endpoints from the router
app.include_router(api_router)