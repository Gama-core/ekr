# app/main.py
import logging
import asyncio
import sys
from fastapi import FastAPI
from app.api.v1.endpoints import agent as agent_router_v1

# --- Set asyncio event loop policy for Windows ---
# This MUST be done before any asyncio operations or FastAPI app instantiation
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# --- End event loop policy setting ---

logging.basicConfig(
    level=logging.INFO, # Changed to INFO for production, DEBUG for development
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Web Query Agent API",
    description="API for processing user queries using LLMs, web search, and crawling.",
    version="0.2.3" # Incremented version
)

app.include_router(
    agent_router_v1.router,
    prefix="/api/v1/agent",
    tags=["V1 - Agent Query"]
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    logger.info("Health check endpoint called.") # Use INFO for less frequent logs
    return {"status": "OK", "message": "API is running"}

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    # No global crawler initialization needed here anymore

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    # No global crawler to close here anymore