import logging
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI

from app.endpoints import router as api_router
from app.config import settings
from app.index_service import build_full_index
from app.llama_ops import initialize_llama_index_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("--- Semantic Retrieval Service Starting Up ---")

    # 1. Initialize LlamaIndex global settings (LLM, Embed Model)
    initialize_llama_index_settings()

    # 2. Ensure vector store directory exists
    Path(settings.VECTOR_STORE_PATH).mkdir(parents=True, exist_ok=True)

    # 3. Build initial index if configured to do so
    if settings.FORCE_REBUILD_ON_STARTUP:
        logger.info("FORCE_REBUILD_ON_STARTUP is True. Starting full index rebuild...")
        await build_full_index(force_rebuild=True)
    else:
        logger.info("FORCE_REBUILD_ON_STARTUP is False. Loading existing index.")
        # The first call to a service function will trigger a lazy load of the index
        # via ensure_vector_index() if it's not already loaded.

    logger.info("Startup process complete.")
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
    return {"status": "OK", "detail": "Service is running."}


app.include_router(api_router, prefix="/rag")

if __name__ == "__main__":
    logger.info(f"Starting Semantic Retrieval Service on http://localhost:8001")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )