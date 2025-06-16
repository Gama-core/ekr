import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

from app.endpoints import router as api_router
from app.config import settings
from app.index_service import build_full_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("--- Semantic Retrieval Service Starting Up ---")
    # Ensure vector store directory exists
    Path(settings.VECTOR_STORE_PATH).mkdir(parents=True, exist_ok=True)
    # Build initial index if needed
    logger.info("Checking/building semantic index on startup...")
    await build_full_index(force_rebuild=settings.FORCE_REBUILD_ON_STARTUP)
    logger.info("Startup index build process complete.")
    yield
    # Shutdown
    logger.info("--- Semantic Retrieval Service Shutting Down ---")

app = FastAPI(
    title="Semantic Retrieval Service",
    description="Handles vector indexing, storage, and retrieval (RAG).",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    # A basic health check. Could be expanded to check API dependencies.
    return {"status": "OK"}

app.include_router(api_router, prefix="/rag") # Prefixing routes for clarity