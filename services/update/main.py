import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx
import uvicorn

from app.endpoints import router as api_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Update Service Starting Up ---")
    try:
        health_url = f"{settings.LLM_QUERY_SERVICE_URL}/health"
        async with httpx.AsyncClient() as client:
            response = await client.get(health_url)
            response.raise_for_status()
        logger.info(f"Connection to LLM Query Service at {health_url} successful.")
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Could not connect to LLM Query Service on startup: {e}")
    yield
    logger.info("--- Update Service Shutting Down ---")

app = FastAPI(
    title="Update Service",
    description="A microservice for intelligently updating note content using an LLM.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "OK"}

app.include_router(api_router)

if __name__ == "__main__":
    logger.info(f"Starting Update Service on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)