# main.py in api-gateway-service

import logging
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

# ADD THIS IMPORT
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ai_assistant_router
from app.routers import notes_router
from app.config import settings
from app.routers import chatbot_router

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

# --- THIS IS THE CRUCIAL PART THAT FIXES THE ERROR ---
# This list defines which frontend URLs are allowed to make requests.
origins = [
    "http://localhost:5173",  # The address of your React development server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)
# --- END OF THE FIX ---

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "OK"}

# Include the routers
app.include_router(notes_router.router)
app.include_router(ai_assistant_router.router)
app.include_router(chatbot_router.router)

if __name__ == "__main__":
    logger.info(f"Starting API Gateway Service on http://{settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT
    )