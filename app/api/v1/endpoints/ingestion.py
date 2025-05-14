# app/api/v1/endpoints/ingestion.py

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form # Added for file upload
)
from sqlalchemy.orm import Session
from typing import Annotated, Optional # Added Optional

from app import schemas
from app.core.database import get_db
from app.services import ingestion_service

router = APIRouter()
DbDependency = Annotated[Session, Depends(get_db)]

# --- Existing /search-and-crawl endpoint ---
@router.post(
    "/search-and-crawl",
    response_model=schemas.ingestion.IngestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Search, Crawl, and Ingest Multiple Web URLs",
    description="Takes a search query, finds relevant URLs, crawls them, and ingests content as new Notes/Documents.",
    tags=["V1 - Ingestion"]
)
async def search_crawl_and_ingest(
    ingestion_request: schemas.ingestion.IngestionRequest,
    db: DbDependency
) -> schemas.ingestion.IngestionResponse:
    # ... (implementation remains the same) ...
    print(f"Received ingestion request for query: '{ingestion_request.query}' ({ingestion_request.num_results} results)")
    try:
        result = await ingestion_service.process_search_and_crawl(db=db, request=ingestion_request)
        print(f"Ingestion process completed for query: '{ingestion_request.query}'")
        return result
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        error_message = f"An unexpected error occurred during the ingestion process for query '{ingestion_request.query}': {type(e).__name__} - {e}"
        print(f"ERROR: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during search-and-crawl ingestion."
        )

# --- NEW ENDPOINT for /ingest/url ---
@router.post(
    "/url",
    response_model=schemas.ingestion.SingleIngestionResult, # Use the new response schema
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Content from a Single URL",
    description="Crawls a single specified URL and ingests its content as a new Note and Document.",
    tags=["V1 - Ingestion"]
)
async def ingest_single_url(
    request: schemas.ingestion.IngestUrlRequest,
    db: DbDependency
) -> schemas.ingestion.SingleIngestionResult:
    try:
        result = await ingestion_service.process_single_url_ingestion(db=db, request=request)
        if result.error: # If service indicates an error in its structured response
            # Decide on HTTP status based on error type, or keep 201 if some processing happened
            # For simplicity, if there's an error string, assume something went wrong enough for a client error
            # However, the service might return partial success, so status 201 might still be okay.
            # Let's assume the service returns a clear error message for failure.
             if "Failed to crawl" in result.message or "No content extracted" in result.message :
                 # If crawl failed or no content, it's not strictly a server error, but request might be "bad"
                 # For now, let's return the result as is, which might have a 201 but an error message.
                 # A more robust way would be for the service to raise HTTPExceptions.
                 pass # Let the result with its message and error pass through
        return result
    except ValueError as ve: # Catch ValueErrors raised by the service for bad inputs/states
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        error_message = f"Unexpected error during single URL ingestion for '{request.url}': {type(e).__name__} - {e}"
        # logger.exception(error_message) # If logger is configured in this file
        print(f"ERROR: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred during URL ingestion: {str(e)}"
        )

# --- NEW ENDPOINT for /ingest/text ---
@router.post(
    "/text",
    response_model=schemas.note.NoteResponse, # Returns the created Note
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Raw Text Content",
    description="Takes raw text and a title, and creates a new Note in the knowledge base.",
    tags=["V1 - Ingestion"]
)
async def ingest_raw_text(
    request: schemas.ingestion.IngestTextRequest,
    db: DbDependency
) -> schemas.note.NoteResponse:
    try:
        created_note = await ingestion_service.process_text_ingestion(db=db, request=request)
        # Convert the SQLAlchemy model instance to a Pydantic response model instance
        # This ensures the response matches the `response_model` annotation.
        # If crud_note.create_note already returns a Pydantic model, this isn't needed.
        # Assuming it returns a SQLAlchemy model:
        return schemas.note.NoteResponse.model_validate(created_note)
    except ValueError as ve: # Catch ValueErrors raised by the service
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        error_message = f"Unexpected error during text ingestion for title '{request.title[:50]}...': {type(e).__name__} - {e}"
        # logger.exception(error_message)
        print(f"ERROR: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred during text ingestion: {str(e)}"
        )

# --- NEW (STUBBED) ENDPOINT for /ingest/file ---
@router.post(
    "/file",
    response_model=schemas.ingestion.SingleIngestionResult, # Or a more specific file ingestion response
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Content from an Uploaded File (Basic Implementation)",
    description="Uploads a file, attempts basic text extraction (TXT, placeholder for PDF), and ingests content as a new Note/Document.",
    tags=["V1 - Ingestion"]
)
async def ingest_from_file(
    db: DbDependency,
    file: UploadFile = File(..., description="The file to upload and ingest."),
    parent_note_id: Optional[int] = Form(None, description="Optional ID of a parent Note."),
    doc_type_id: Optional[int] = Form(None, description="Optional DocumentType ID for the created Document."),
    note_type_id: Optional[int] = Form(None, description="Optional NoteType ID for the created Note.")
):
    try:
        created_note, created_doc, error_msg = await ingestion_service.process_file_ingestion(
            db=db,
            file=file,
            parent_note_id=parent_note_id,
            doc_type_id_form=doc_type_id,
            note_type_id_form=note_type_id
        )

        if error_msg:
            # If the service returns an error message, it implies failure.
            # Consider raising HTTPException directly from the service for better control.
            # For now, we map it to a 400 or 500 based on content.
            status_code = status.HTTP_400_BAD_REQUEST if "Failed to save" in error_msg or "Could not extract" in error_msg else status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=error_msg)

        return schemas.ingestion.SingleIngestionResult(
            message="File ingested successfully.",
            note_id=created_note.id if created_note else None,
            document_id=created_doc.id if created_doc else None,
            url_processed=file.filename # Use filename as an identifier here
        )
    except HTTPException as http_exc:
        raise http_exc # Re-raise if service already raised one
    except Exception as e:
        error_message = f"Unexpected error during file ingestion for '{file.filename}': {type(e).__name__} - {e}"
        # logger.exception(error_message)
        print(f"ERROR: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred during file ingestion: {str(e)}"
        )