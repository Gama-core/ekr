# app/main.py
import logging
from fastapi import FastAPI
from app.api.v1.endpoints import agent as agent_router_v1
# from app.services import web_crawler # No longer need to import for startup/shutdown hooks

logging.basicConfig(
    level=logging.DEBUG, # Keep DEBUG for now
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Web Query Agent API",
    description="API for processing user queries using LLMs, web search, and crawling.",
    version="0.2.2" # Incremented version
)

app.include_router(
    agent_router_v1.router,
    prefix="/api/v1/agent",
    tags=["V1 - Agent Query"]
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    logger.debug("Health check endpoint called.")
    return {"status": "OK", "message": "API is running"}

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    # No global crawler initialization needed here anymore
    # await web_crawler.initialize_crawler() # REMOVE THIS
    # logger.info("Web crawler initialization attempted on startup.") # REMOVE THIS

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    # No global crawler to close here anymore
    # await web_crawler.close_crawler() # REMOVE THIS