# app/api/v1/api.py
from fastapi import APIRouter

# Import your endpoint routers
from .endpoints import assistant as assistant_router
from .endpoints import ingestion as ingestion_router
from .endpoints import notes as notes_router
from .endpoints import documents as documents_router
from .endpoints import links as links_router

# This is the router instance for all V1 API endpoints.
# It will be imported by the top-level API router.
api_router_v1 = APIRouter()

# Include Assistant router
api_router_v1.include_router(
    assistant_router.router,
    prefix="/assistant",
    tags=["V1 - Assistant Query"]
)

# Include Ingestion router
api_router_v1.include_router(
    ingestion_router.router,
    prefix="/ingest",
    tags=["V1 - Ingestion"]
)
# Note: If you later decide to move ingestion under /kb, change the prefix:
# e.g., prefix="/kb/ingest", tags=["V1 - KB - Ingestion"]

# Include Notes router for Knowledge Base management
api_router_v1.include_router(
    notes_router.router,
    prefix="/kb/notes",
    tags=["V1 - KB - Notes"]
)


api_router_v1.include_router(
    documents_router.router,
    prefix="/kb/documents",
    tags=["V1 - KB - Documents"]
)



api_router_v1.include_router(
    links_router.router,
    prefix="/kb/links",
    tags=["V1 - KB - Links"]
)