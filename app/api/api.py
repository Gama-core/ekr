# app\api\api.py
from fastapi import APIRouter
from .v1.api import api_router as api_v1_router

api_router = APIRouter()

# Include versioned routers
api_router.include_router(api_v1_router, prefix="/v1")

# Add other top-level or version-independent routes here if needed
