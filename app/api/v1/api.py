# app/api/v1/api.py
from fastapi import APIRouter

# Import your endpoint routers
from .endpoints import assistant as assistant_router
from .endpoints import ingestion as ingestion_router
from .endpoints import notes as notes_router
from .endpoints import documents as documents_router
from .endpoints import links as links_router
from .endpoints import note_types as note_types_router         # <-- ADDED IMPORT
from .endpoints import document_types as document_types_router # <-- ADDED IMPORT

# This is the router instance for all V1 API endpoints.
# It will be imported by the top-level API router (app/api/api.py).
api_router_v1 = APIRouter()

# --- Assistant API ---
api_router_v1.include_router(
    assistant_router.router,
    prefix="/assistant",
    tags=["V1 - Assistant Query"]
)

# --- Ingestion API ---
# Included ONCE. The prefix determines its final path (/api/v1/ingest)
api_router_v1.include_router(
    ingestion_router.router,
    prefix="/ingest", # All ingestion endpoints under /api/v1/ingest/...
    tags=["V1 - Ingestion"]
)

# --- Knowledge Base (KB) Management APIs ---
api_router_v1.include_router(
    notes_router.router,
    prefix="/kb/notes", # Path: /api/v1/kb/notes/...
    tags=["V1 - KB - Notes"]
)
api_router_v1.include_router(
    documents_router.router,
    prefix="/kb/documents", # Path: /api/v1/kb/documents/...
    tags=["V1 - KB - Documents"]
)
api_router_v1.include_router(
    links_router.router,
    prefix="/kb/links", # Path: /api/v1/kb/links/...
    tags=["V1 - KB - Links"]
)

# --- KB Type Management APIs ---
api_router_v1.include_router(
    note_types_router.router,
    prefix="/kb/note-types", # Path: /api/v1/kb/note-types/...
    tags=["V1 - KB - Note Types"]
)
api_router_v1.include_router(
    document_types_router.router,
    prefix="/kb/document-types", # Path: /api/v1/kb/document-types/...
    tags=["V1 - KB - Document Types"]
)

