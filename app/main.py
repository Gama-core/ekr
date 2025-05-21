# app/main.py
import logging
import asyncio
import sys
from fastapi import FastAPI

# Core application imports.
from app.core.config import settings
from app.api.api import api_router as application_api_router # Top-level API router.

# Platform-specific asyncio event loop policy for Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Basic logging configuration.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__) # Logger for this module.

# FastAPI application instance.
app = FastAPI(
    title="Feature-First AI Knowledge Engine API",
    description="API for intelligent web interaction, LLM processing, and internal RAG.",
    version="1.0.1" # Incremented version.
)

# Include the main application API router with a /api prefix.
app.include_router(application_api_router, prefix="/api")

# Health check endpoint.
@app.get("/health", tags=["Health Check"], summary="API Health Status")
async def health_check():
    logger.info("Health check endpoint called.")
    return {"status": "OK", "message": "API is running."}

# Application startup event handler.
@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    logger.info(f"UPLOAD_DIR: {settings.UPLOAD_DIR.resolve()}")
    logger.info(f"VECTOR_STORE_PATH: {settings.VECTOR_STORE_PATH}")
    # Placeholder for future initializations like vector store client.
    # from app.features.knowledge_index.vector_store_service import get_vector_store_client
    # try:
    #     client = get_vector_store_client()
    #     logger.info(f"Vector store client initialized for path: {settings.VECTOR_STORE_PATH}")
    # except Exception as e:
    #     logger.error(f"Failed to initialize vector store client on startup: {e}", exc_info=True)
    logger.info("Application startup complete.")

# Application shutdown event handler.
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    # Placeholder for cleanup tasks.
    logger.info("Application shutdown complete.")