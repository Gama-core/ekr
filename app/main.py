# app/main.py
import logging
import asyncio
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Core application imports.
from app.core.config import settings  # Import the settings instance
from app.core.config import ensure_directories_exist  # Import the standalone function
from app.core.database import SessionLocal, check_db_connection
from app.api.api import api_router as application_api_router

# Feature specific imports for startup
from app.features.semantic_retrieval.index_service import build_full_index as build_semantic_index
from app.features.semantic_retrieval.config import semantic_retrieval_config

# Setup logging (assuming it's already well-configured)
# Set asyncio event loop policy for Windows if needed
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(  # Basic config, adjust as needed
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]  # Ensure logs go to stdout for uvicorn
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Application starting up...")

    # ensure_directories_exist() is now called at the end of config.py,
    # so it should have already run by the time this lifespan event starts.
    # However, calling it again here is harmless and ensures it if the import order
    # somehow got tricky, or if you move it from config.py's end.
    # For robustness:
    ensure_directories_exist()

    logger.info(f"UPLOAD_DIR: {settings.UPLOAD_DIR.resolve()}")
    logger.info(f"VECTOR_STORE_PATH: {settings.VECTOR_STORE_PATH.resolve()}")

    if check_db_connection():
        logger.info("Database connection successful. Proceeding with RAG index check/build.")
        db_session_for_startup = SessionLocal()
        try:
            logger.info(
                f"Building/Loading semantic retrieval index. "
                f"Force rebuild: {semantic_retrieval_config.FORCE_REBUILD_ON_STARTUP}"
            )
            await build_semantic_index(db_session_for_startup,
                                       force_rebuild=semantic_retrieval_config.FORCE_REBUILD_ON_STARTUP)
            logger.info("Semantic retrieval index build/load process completed.")
        except Exception as e:
            logger.error(f"Failed to build/load semantic retrieval index on startup: {e}", exc_info=True)
        finally:
            db_session_for_startup.close()
    else:
        logger.error("Database connection failed. Semantic retrieval index cannot be built/loaded.")

    logger.info("Application startup complete.")
    yield

    # Shutdown logic
    logger.info("Application shutting down...")
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="Feature-First AI Knowledge Engine API",
    description="API for intelligent web interaction, LLM processing, and semantic retrieval (RAG).",
    version="1.1.0",
    lifespan=lifespan
)

app.include_router(application_api_router, prefix="/api")


@app.get("/health", tags=["Health Check"], summary="API Health Status")
async def health_check():
    logger.info("Health check endpoint called.")
    return {"status": "OK", "message": "API is running."}