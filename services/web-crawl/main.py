import asyncio
import sys
import logging

# --- FIX for Windows + Playwright ---
# This MUST be at the top of the file before other asyncio-based libraries are imported.
import sys, asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from app.endpoints import router as api_router
from app.config import settings

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- Web Crawl Service Starting Up ---")
    yield
    logger.info("--- Web Crawl Service Shutting Down ---")

app = FastAPI(
    title="Web Crawl Service",
    description="A microservice for crawling web pages and extracting content.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "OK"}

app.include_router(api_router)

if __name__ == "__main__":
    logger.info(f"Starting Web Crawl Service on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT
    )