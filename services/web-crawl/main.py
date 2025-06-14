import logging
import asyncio
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.endpoints import router as api_router

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# --- FIX for Windows + Playwright ---
# Set asyncio event loop policy for Windows before any async operations start.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# --- END OF FIX ---

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