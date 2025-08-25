# main.py
import logging
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers import notes_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- API Gateway Service Starting Up ---")
    yield
    logger.info("--- API Gateway Service Shutting Down ---")

app = FastAPI(
    title="API Gateway Service",
    description="The single entry point for all client applications.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "OK"}

# Include the routers
app.include_router(notes_router.router)

if __name__ == "__main__":
    logger.info(f"Starting API Gateway Service on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True
    )