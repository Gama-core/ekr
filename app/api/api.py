# D:\PFE\V_01\app\api\api.py
from fastapi import APIRouter
# Import the V1 API aggregator from app.api.v1.api
from .v1.api import api_router_v1 as v1_api_aggregator_router

# This is the main application API router that will be included in app.main
api_router = APIRouter()

# Include the V1 API router, prefixing all its routes with /v1
api_router.include_router(v1_api_aggregator_router, prefix="/v1")

# Add other top-level or version-independent routes here if needed in the future