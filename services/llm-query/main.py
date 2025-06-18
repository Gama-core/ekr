import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

# Import from the app package
from app.endpoints import router as api_router
from app.service import initialize_llm_client
from app.config import settings

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("--- LLM Query Service Starting Up ---")
    initialize_llm_client()
    yield
    # Shutdown
    logger.info("--- LLM Query Service Shutting Down ---")

app = FastAPI(
    title="LLM Query Service",
    description="A centralized microservice for interacting with Large Language Models.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Checks if the service is running and the LLM client is configured."""
    if not settings.QWEN_API_KEY:
        return {"status": "degraded", "detail": "QWEN_API_KEY is not configured."}
    return {"status": "OK"}


app.include_router(api_router)


if __name__ == "__main__":
    logger.info(f"Starting LLM Query Service on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)