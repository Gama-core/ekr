# app/main.py
import logging
import asyncio
import sys
from fastapi import FastAPI

# --- Import Routers ---
# Remove or comment out the old agent router import if it's being replaced
# from app.api.v1.endpoints import agent as agent_router_v1
from app.api.v1.endpoints import assistant as assistant_router_v1 # <-- Import the new assistant router
# Import the main API router if you intend to include other endpoints like ingestion
from app.api.api import api_router as main_api_router # Assuming this includes ingestion, kb, etc.

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
    title="AI Knowledge Management & Assistant API", # Updated Title
    description="API for knowledge management and processing user queries using LLMs, RAG, web search, and crawling.", # Updated Description
    version="0.3.0" # Incremented version
)

# --- Include Routers ---

# Include the new Assistant router
app.include_router(
    assistant_router_v1.router, # <-- Use the new assistant router variable
    prefix="/api/v1/assistant", # <-- Use the new prefix
    tags=["V1 - Assistant Query"] # <-- Use the new tag
)

# Remove or comment out the old agent router inclusion
# app.include_router(
#     agent_router_v1.router,
#     prefix="/api/v1/agent",
#     tags=["V1 - Agent Query"] # Deprecated tag
# )

# Include the main API router which should contain ingestion, kb, etc.
# This assumes app/api/api.py and app/api/v1/api.py are set up to route ingestion etc.
app.include_router(main_api_router, prefix="/api") # Includes /api/v1/ingest/* etc.


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