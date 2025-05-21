# app/api/v1/api.py
from fastapi import APIRouter

# Import feature endpoint routers.
# Only import routers for features that are currently being implemented or are stable.
from app.features.web_interaction.endpoints import router as web_interaction_router

# Placeholder for assistant_router if it's being refactored into the new structure.
# Ensure this path is correct once app/features/assistant/endpoints.py exists.
# from app.features.assistant.endpoints import router as assistant_router

# --- V1 API Router ---
# This router aggregates all feature-specific routers for version 1 of the API.
api_router_v1 = APIRouter()

# Include the Web Interaction feature router.
api_router_v1.include_router(
    web_interaction_router,
    prefix="/web", # Routes will be /api/v1/web/...
    tags=["V1 - Web Interaction"] # Groups endpoints in Swagger UI.
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