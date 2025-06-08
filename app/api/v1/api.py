# app/api/v1/api.py
from fastapi import APIRouter

# Import feature endpoint routers.
from app.features.google_search.endpoints import router as google_search_router
from app.features.web_crawl.endpoints import router as web_crawl_router
from app.features.llm_query.endpoints import router as llm_query_router
from app.features.semantic_retrieval.endpoints import router as semantic_retrieval_router
from app.features.ocr.endpoints import router as ocr_router
from app.features.quiz.endpoints import router as quiz_router
from app.features.rss_extractor.endpoints import router as rss_extractor_router

# --- V1 API Router ---
# This router aggregates all feature-specific routers for version 1 of the API.
api_router_v1 = APIRouter()

# Include the Google Search feature router.
api_router_v1.include_router(
    google_search_router,
    prefix="/search",
    tags=["V1 - Google Search"]
)

# Include the Web Crawl feature router.
api_router_v1.include_router(
    web_crawl_router,
    prefix="/crawl",
    tags=["V1 - Web Crawl"]
)

# Include the LLM Query feature router.
api_router_v1.include_router(
    llm_query_router,
    prefix="/llm",
    tags=["V1 - LLM Query"]
)

# Include the Semantic Retrieval (RAG) feature router
api_router_v1.include_router(
    semantic_retrieval_router,
    prefix="/semantic-retrieval",
    tags=["V1 - Semantic Retrieval (RAG)"]
)

# Include the OCR feature router.
api_router_v1.include_router(
    ocr_router,
    prefix="/ocr",
    tags=["V1 - OCR"]
)

# --- Include the Quiz feature router ---
api_router_v1.include_router(
    quiz_router,
    prefix="/quiz",
    tags=["V1 - Quiz"]
)

# --- Include the RSS Extractor feature router ---
api_router_v1.include_router(
    rss_extractor_router,
    prefix="/rss",
    tags=["V1 - RSS Extractor"]
)