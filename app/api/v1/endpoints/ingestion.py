# app/api/v1/endpoints/ingestion.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated # Use Annotated for cleaner dependency/parameter metadata (optional but nice)

# Import schemas used by this endpoint
from app import schemas

# Import the database session dependency
from app.core.database import get_db

# Import the service layer functions (we'll create these next)
# Use a try-except block for now to avoid errors if service file doesn't exist yet
try:
    from app.services import ingestion_service
except ImportError:
    # Define a placeholder if the service doesn't exist yet
    # This allows the API to start, but calls will fail until service is implemented
    class MockIngestionService:
        async def process_search_and_crawl(self, db: Session, request: schemas.ingestion.IngestionRequest):
            # Simulate finding URLs but failing to process
            print("WARNING: Using mock ingestion_service. Implement the actual service.")
            results = [{"url": f"http://example.com/{i}", "status": "mock_service"} for i in range(request.num_results)]
            return schemas.ingestion.IngestionResponse(
                message="Mock service response: Service not implemented.",
                processed_urls=[schemas.ingestion.ProcessedUrlResult(**res) for res in results]
            )
    ingestion_service = MockIngestionService()
    print("Warning: Ingestion service module not found, using mock.")


# Create an API Router specific to ingestion endpoints
router = APIRouter()

# Define type alias for the database session dependency for cleaner code
DbDependency = Annotated[Session, Depends(get_db)]

@router.post(
    "/search-and-crawl",
    response_model=schemas.ingestion.IngestionResponse,
    status_code=status.HTTP_200_OK, # Explicitly set success status code
    summary="Search, Crawl, and Ingest Web Content",
    description="""
Takes a search query, finds relevant URLs using Google Search,
crawls the content of those URLs using Crawl4AI, extracts relevant text,
and stores the results as new Document and Note entries in the database.
""",
    tags=["Ingestion"] # Group endpoint in Swagger UI
)
async def search_crawl_and_ingest(
    ingestion_request: schemas.ingestion.IngestionRequest, # Request body validated against schema
    db: DbDependency # Inject database session using Annotated dependency
) -> schemas.ingestion.IngestionResponse:
    """
    API endpoint to trigger the web search, crawling, and ingestion process.
    """
    print(f"Received ingestion request for query: '{ingestion_request.query}' ({ingestion_request.num_results} results)")
    try:
        # --- Call the Service Layer ---
        # This function will contain the core logic (search, crawl, save)
        result = await ingestion_service.process_search_and_crawl(db=db, request=ingestion_request)
        # --- Service Layer Call End ---

        print(f"Ingestion process completed for query: '{ingestion_request.query}'")
        # The service function should return data matching IngestionResponse schema
        return result

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly (e.g., validation errors from service)
        raise http_exc
    except Exception as e:
        # Catch any unexpected errors during the process
        error_message = f"An unexpected error occurred during the ingestion process for query '{ingestion_request.query}': {type(e).__name__} - {e}"
        print(f"ERROR: {error_message}")
        # Optionally log the full traceback here using the logging module

        # Return a generic 500 error to the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during ingestion."
        )