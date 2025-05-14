# app/main.py
import logging
import asyncio
import sys
from fastapi import FastAPI

# --- Import ONLY the top-level aggregated API router ---
from app.api.api import api_router as application_api_router

# --- Set asyncio event loop policy for Windows ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# --- End event loop policy setting ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Knowledge Management & Assistant API",
    description="API for knowledge management and processing user queries using LLMs, RAG, web search, and crawling.",
    version="0.3.1" # Increment version slightly for this fix
)

# --- Include the single, aggregated application API router ---
# This one line will make all your versioned API endpoints available
# (e.g., /api/v1/assistant/*, /api/v1/ingest/*, /api/v1/kb/notes/*)
app.include_router(application_api_router, prefix="/api")


@app.get("/health", tags=["Health Check"])
async def health_check():
    logger.info("Health check endpoint called.")
    return {"status": "OK", "message": "API is running"}

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    # Any startup logic

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    # Any shutdown logic