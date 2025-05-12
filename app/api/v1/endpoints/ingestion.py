# app/api/v1/endpoints/ingestion.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated

from app import schemas
from app.core.database import get_db
# Import the REAL service
from app.services import ingestion_service # <--- CHANGE HERE

router = APIRouter()
DbDependency = Annotated[Session, Depends(get_db)]

@router.post(
    "/search-and-crawl",
    response_model=schemas.ingestion.IngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Search, Crawl, and Ingest Web Content",
    description="...", # Keep description
    tags=["Ingestion"]
)
async def search_crawl_and_ingest(
    ingestion_request: schemas.ingestion.IngestionRequest,
    db: DbDependency
) -> schemas.ingestion.IngestionResponse:
    """
    API endpoint to trigger the web search, crawling, and ingestion process.
    """
    print(f"Received ingestion request for query: '{ingestion_request.query}' ({ingestion_request.num_results} results)")
    try:
        # --- Call the REAL Service Layer --- <--- CHANGE HERE
        result = await ingestion_service.process_search_and_crawl(db=db, request=ingestion_request)
        # --- Service Layer Call End ---

        print(f"Ingestion process completed for query: '{ingestion_request.query}'")
        return result

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        error_message = f"An unexpected error occurred during the ingestion process for query '{ingestion_request.query}': {type(e).__name__} - {e}"
        print(f"ERROR: {error_message}")
        # logger.exception(error_message) # Use logger if configured
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during ingestion."
        )