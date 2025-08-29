import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn  # <-- ADD THIS IMPORT

from app.endpoints import router as api_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- OCR Service Starting Up ---")
    if not settings.MISTRAL_API_KEY:
        logger.warning("Service is starting in a degraded state. API calls will fail until configured.")
    yield
    logger.info("--- OCR Service Shutting Down ---")

app = FastAPI(
    title="OCR Service",
    description="A microservice for performing OCR on documents and images via Mistral AI.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    if not settings.MISTRAL_API_KEY:
        return {"status": "degraded", "detail": "MISTRAL_API_KEY is not configured."}
    return {"status": "OK"}

app.include_router(api_router)

# --- ADD THIS BLOCK AT THE END OF THE FILE ---
if __name__ == "__main__":
    logger.info(f"Starting OCR Service on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True
    )