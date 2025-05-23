# app/api/v1/api.py
from fastapi import APIRouter

# Import feature endpoint routers.
from app.features.google_search.endpoints import router as google_search_router
from app.features.web_crawl.endpoints import router as web_crawl_router

# Placeholder for assistant_router if it's being refactored into the new structure.
# from app.features.assistant.endpoints import router as assistant_router

# --- V1 API Router ---
# This router aggregates all feature-specific routers for version 1 of the API.
api_router_v1 = APIRouter()

# Include the Google Search feature router.
api_router_v1.include_router(
    google_search_router,
    prefix="/search", # Routes will be /api/v1/search/...
    tags=["V1 - Google Search"] # Groups endpoints in Swagger UI.
)

# Include the Web Crawl feature router.
api_router_v1.include_router(
    web_crawl_router,
    prefix="/crawl", # Routes will be /api/v1/crawl/...
    tags=["V1 - Web Crawl"] # Groups endpoints in Swagger UI.
)

# Placeholder for the Assistant feature router.
# Uncomment and adjust once app/features/assistant/endpoints.py is ready.
# api_router_v1.include_router(
#     assistant_router,
#     prefix="/assistant",
#     tags=["V1 - Assistant Query"]
# )

# Future feature routers will be included here:
# e.g., LLM Query, Knowledge Index, RAG Retrieval, Ingestion & Indexing.