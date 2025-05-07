# app\api\v1\api.py
from fastapi import APIRouter
from .endpoints import ingestion # Import your endpoint routers here

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(ingestion.router, prefix="/ingest", tags=["Ingestion"])
# Add other v1 endpoint routers here (e.g., notes, documents, users)

