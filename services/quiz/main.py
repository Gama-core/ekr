import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx

from app.endpoints import router as api_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Quiz Service Starting Up ---")
    # Check connectivity to the dependent LLM service on startup
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.LLM_QUERY_SERVICE_URL}/health")
            response.raise_for_status()
        logger.info("Connection to LLM Query Service successful.")
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Could not connect to LLM Query Service on startup: {e}")
    yield
    logger.info("--- Quiz Service Shutting Down ---")

app = FastAPI(
    title="Quiz Generation Service",
    description="A microservice for generating quizzes using an LLM.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Checks if the service is running."""
    # A more advanced health check could re-verify connection to the LLM service.
    return {"status": "OK"}

app.include_router(api_router)