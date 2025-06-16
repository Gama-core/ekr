import logging
import asyncio
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx

from app.config import settings
from app.endpoints import router as api_router
from app.index_service import build_full_index
from app.clients.database_client import database_client

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Windows fix for LlamaIndex/HuggingFace tokenizers if needed
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    logger.info("--- Semantic Retrieval Service Starting Up ---")

    # 1. Check connectivity to the dependent database-api service
    try:
        health_url = str(settings.DATABASE_API_URL).rstrip('/') + "/health"
        async with httpx.AsyncClient() as client:
            response = await client.get(health_url)
            response.raise_for_status()
        logger.info("Connection to Database API Service successful.")

        # 2. Build the index on startup
        logger.info(f"Building/Loading semantic index. Force rebuild: {settings.FORCE_REBUILD_ON_STARTUP}")
        await build_full_index(force_rebuild=settings.FORCE_REBUILD_ON_STARTUP)
        logger.info("Semantic index build/load process completed.")

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Could not connect to Database API Service on startup: {e}. Index will not be built.")
    except Exception as e:
        logger.exception(f"Failed to build semantic index on startup: {e}")

    yield
    # --- Shutdown Logic ---
    logger.info("--- Semantic Retrieval Service Shutting Down ---")


app = FastAPI(
    title="Semantic Retrieval (RAG) Service",
    description="A microservice for indexing and retrieving context using a vector store.",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Checks if the service is running."""
    # A more advanced check could query the index for its stats.
    return {"status": "OK"}


# Include all API endpoints
app.include_router(api_router)