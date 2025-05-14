# app/services/ingestion_service.py
import logging
import asyncio
from typing import Optional, List, Tuple

# --- NEW IMPORTS ADDED HERE ---
import os  # For os.remove and os.path.splitext (though Path.suffix is better for ext)
import shutil  # For shutil.copyfileobj
from pathlib import Path  # For Path objects
from fastapi import UploadFile  # For type hinting the file parameter
# --- END NEW IMPORTS ---

from sqlalchemy.orm import Session
from app import schemas, models
from app.services import google_search, web_crawler, llm_service
from app.services.crud import (
    crud_document, crud_document_type,
    crud_note, crud_note_type,
    crud_note_document
)
from app.core.config import settings  # Assuming UPLOAD_DIR might move here eventually
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig
from playwright.async_api import Error as PlaywrightError

logger = logging.getLogger(__name__)

NOTE_TEXT_MAX_LENGTH_FOR_SCHEMA = 4000

# Define UPLOAD_DIR here if it's specific to this service, or import from config if global
# This was defined in endpoints/documents.py, ensure consistency or centralize it
# For now, let's define it here for the service to be self-contained regarding its needs.
# If endpoints/documents.py also uses it, it should be defined in a common place (e.g., config)
# and imported by both. For this example, let's assume it's defined here for now.
UPLOAD_DIR_SERVICE_COPY = Path("./uploaded_files")  # Using a distinct name to avoid confusion
UPLOAD_DIR_SERVICE_COPY.mkdir(parents=True, exist_ok=True)  # Ensure it exists for this service


async def generate_title_for_content(url: Optional[str], text_content: Optional[str]) -> str:
    if not text_content:
        if url:
            # Use Path to get filename if url is a local path string
            if os.path.exists(url):  # Check if it's a local file path
                return Path(url).name
            return url.split('/')[-1] or url.split('/')[-2] or "Ingested Content from " + url
        return "Untitled Ingested Content"

    try:
        source_info = f"scraped from {url}" if url else "provided directly"
        prompt = f"Generate a concise, descriptive title (max 10 words) for the following content {source_info}:\n\nCONTEXT抜粋:\n{text_content[:1500]}\n\nTITLE:"
        title = await llm_service.generate_llm_response(
            system_prompt="You are a title generation assistant.",
            user_prompt=prompt,
            max_tokens=30,
            temperature=0.3
        )
        if title and "Error:" not in title:
            return title.strip().strip('"')
    except Exception as e:
        logger.error(f"LLM title generation failed for content from {url or 'direct text'}: {e}")

    first_sentence = text_content.split('.')[0]
    return (first_sentence[:100] + '...') if len(first_sentence) > 100 else first_sentence


async def _persist_crawled_content(
        db: Session,
        url: Optional[str],
        extracted_text: str,
        parent_note_id: Optional[int] = None,
        custom_title: Optional[str] = None,
        document_path_for_db: Optional[str] = None,  # For file ingestion, path might be different from URL
        document_mime_type: Optional[str] = "text/markdown"  # Default for crawled web content
) -> Tuple[Optional[models.Note], Optional[models.Document], Optional[str]]:
    try:
        note_type = crud_note_type.get_or_create_note_type(db, name="Ingested Content")  # More generic
        created_document = None
        doc_name = "Document for content"

        if url or document_path_for_db:  # Create a document if there's a URL or a specific path for it
            doc_type_name = "Web Page" if url and not document_path_for_db else "Uploaded File"
            doc_type = crud_document_type.get_or_create_document_type(db, name=doc_type_name)

            if url and not document_path_for_db:  # It's a web URL
                path_for_doc = url
                doc_name = url.split('/')[-1] or url.split('/')[-2] or f"Web Document for {url}"
            elif document_path_for_db:  # It's a file path
                path_for_doc = document_path_for_db  # This should be the filename stored in DB
                doc_name = Path(document_path_for_db).name  # Use the filename as doc name
            else:  # Should not happen if logic is correct
                path_for_doc = "unknown_source"

            doc_schema = schemas.DocumentCreate(
                doc_type_id=doc_type.id,
                comment=f"Content ingested from {url or document_path_for_db or 'unknown source'}",
                mime_type=document_mime_type,
                url=url,  # Store original URL if it's a web source
                path=path_for_doc,
                name=doc_name
            )
            created_document = crud_document.create_document(db=db, doc_in=doc_schema, owner_id=settings.SYSTEM_USER_ID)
            logger.info(f"Created Document ID: {created_document.id} for source: {url or document_path_for_db}")

        text_for_note_schema = extracted_text[:NOTE_TEXT_MAX_LENGTH_FOR_SCHEMA]
        if len(extracted_text) > NOTE_TEXT_MAX_LENGTH_FOR_SCHEMA:
            logger.warning(f"Extracted text for Note ({len(extracted_text)} chars) exceeds max length. Truncating.")

        note_title = custom_title if custom_title else await generate_title_for_content(url or document_path_for_db,
                                                                                        text_for_note_schema)

        note_schema = schemas.NoteCreate(
            title=note_title,
            text=text_for_note_schema,
            type_id=note_type.id,
            parent_id=parent_note_id,
            owner_id=settings.SYSTEM_USER_ID
        )
        created_note = crud_note.create_note(db=db, note_in=note_schema, owner_id=settings.SYSTEM_USER_ID)
        logger.info(
            f"Created Note ID: {created_note.id} for content from {url or document_path_for_db or 'direct text'}")

        if created_document and created_note:
            crud_note_document.create_note_document_link(
                db=db, note_id=created_note.id, document_id=created_document.id
            )
            logger.info(f"Linked Note ID {created_note.id} and Document ID {created_document.id}")

        return created_note, created_document, None

    except Exception as e_db:
        logger.exception(
            f"Database error during persistence for content from {url or document_path_for_db or 'direct text'}")
        return None, None, f"DB Error: {type(e_db).__name__} - {str(e_db)}"


async def process_search_and_crawl(
        db: Session,
        request: schemas.ingestion.IngestionRequest
) -> schemas.ingestion.IngestionResponse:
    logger.info(f"Starting ingestion process for query: '{request.query}', num_results: {request.num_results}")
    processed_urls_results: List[schemas.ingestion.ProcessedUrlResult] = []

    try:
        urls_to_process = await google_search.search_web(query=request.query, num_results=request.num_results)
        if not urls_to_process:
            return schemas.ingestion.IngestionResponse(message="No URLs found for the search query.", processed_urls=[])
        logger.info(f"Found {len(urls_to_process)} URLs to process: {urls_to_process}")
    except Exception as e_search:
        logger.exception(f"Error during Google Search for query '{request.query}'")
        return schemas.ingestion.IngestionResponse(message=f"Failed during web search: {str(e_search)}",
                                                   processed_urls=[])

    for target_url in urls_to_process:
        current_result_payload = {"url": target_url, "status": "pending"}
        extracted_text: Optional[str] = None
        crawl_error: Optional[str] = None

        logger.debug(f"Attempting to crawl: {target_url}")
        try:
            browser_cfg = BrowserConfig(headless=True, verbose=False)
            timeout_seconds = 60
            async with asyncio.timeout(timeout_seconds):
                async with AsyncWebCrawler(config=browser_cfg) as crawler:
                    extracted_text = await web_crawler.crawl_and_extract_with_instance(
                        crawler_instance=crawler, url=target_url
                    )
            if not extracted_text:
                crawl_error = "No usable content extracted"
            else:
                logger.info(f"Successfully extracted ~{len(extracted_text)} chars from {target_url}")
        except asyncio.TimeoutError:
            crawl_error = f"Crawl timed out ({timeout_seconds}s)"
        except PlaywrightError as pe:
            crawl_error = f"Playwright Error: {type(pe).__name__}"
        except Exception as e_crawl:
            crawl_error = f"Unexpected crawl error: {type(e_crawl).__name__}"
            logger.exception(f"Unexpected error crawling {target_url}")

        if crawl_error:
            current_result_payload["status"] = "crawl_failed"
            current_result_payload["error"] = crawl_error
            current_result_payload["message"] = f"Crawl failed: {crawl_error}"
            processed_urls_results.append(schemas.ingestion.ProcessedUrlResult(**current_result_payload))
            continue

        if extracted_text:
            created_note, created_doc, db_error = await _persist_crawled_content(
                db, url=target_url, extracted_text=extracted_text
            )
            if db_error:
                current_result_payload["status"] = "db_error"
                current_result_payload["error"] = db_error
                current_result_payload["message"] = f"DB error: {db_error}"
            else:
                current_result_payload["status"] = "success"
                current_result_payload["note_id"] = created_note.id if created_note else None
                current_result_payload["document_id"] = created_doc.id if created_doc else None
                current_result_payload["message"] = "Content ingested successfully."
        else:
            current_result_payload["status"] = "no_content_to_persist"
            current_result_payload["error"] = "No content extracted from URL to persist."
            current_result_payload["message"] = "No content extracted to persist."

        processed_urls_results.append(schemas.ingestion.ProcessedUrlResult(**current_result_payload))

    final_message = f"Ingestion process completed for query '{request.query}'. Processed {len(processed_urls_results)} URLs."
    logger.info(final_message)
    return schemas.ingestion.IngestionResponse(message=final_message, processed_urls=processed_urls_results)


async def process_single_url_ingestion(
        db: Session,
        request: schemas.ingestion.IngestUrlRequest
) -> schemas.ingestion.SingleIngestionResult:
    logger.info(f"Starting single URL ingestion for: {request.url}")
    target_url_str = str(request.url)
    extracted_text: Optional[str] = None
    crawl_error: Optional[str] = None
    identifier = target_url_str

    try:
        browser_cfg = BrowserConfig(headless=True, verbose=False)
        timeout_seconds = 60
        async with asyncio.timeout(timeout_seconds):
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                extracted_text = await web_crawler.crawl_and_extract_with_instance(
                    crawler_instance=crawler, url=target_url_str
                )
        if not extracted_text:
            crawl_error = "No usable content extracted"
    except asyncio.TimeoutError:
        crawl_error = f"Crawl timed out ({timeout_seconds}s)"
    except PlaywrightError as pe:
        crawl_error = f"Playwright Error: {type(pe).__name__}"
    except Exception as e_crawl:
        crawl_error = f"Unexpected crawl error: {type(e_crawl).__name__}"
        logger.exception(f"Unexpected error crawling {target_url_str}")

    if crawl_error:
        return schemas.ingestion.SingleIngestionResult(
            message=f"Failed to crawl URL: {crawl_error}", error=crawl_error, identifier_processed=identifier
        )

    if extracted_text:
        created_note, created_doc, db_error = await _persist_crawled_content(
            db, url=target_url_str, extracted_text=extracted_text, parent_note_id=request.parent_note_id
        )
        if db_error:
            return schemas.ingestion.SingleIngestionResult(
                message=f"Database error after crawling: {db_error}", error=db_error, identifier_processed=identifier
            )
        return schemas.ingestion.SingleIngestionResult(
            message="URL ingested successfully.",
            note_id=created_note.id if created_note else None,
            document_id=created_doc.id if created_doc else None,
            identifier_processed=identifier
        )
    else:
        return schemas.ingestion.SingleIngestionResult(
            message="No content extracted from URL to persist.", error="No content extracted",
            identifier_processed=identifier
        )


async def process_text_ingestion(
        db: Session,
        request: schemas.ingestion.IngestTextRequest
) -> models.Note:  # Returning the model, endpoint will convert to schema
    logger.info(f"Starting text ingestion for title: '{request.title[:50]}...'")
    created_note, _, db_error = await _persist_crawled_content(
        db,
        url=None,
        extracted_text=request.text_content,
        parent_note_id=request.parent_note_id,
        custom_title=request.title
    )
    if db_error:
        raise ValueError(f"Database error during text ingestion: {db_error}")
    if not created_note:
        raise ValueError("Failed to create note from text ingestion.")
    return created_note


async def process_file_ingestion(
        db: Session,
        file: UploadFile,  # Type hint for UploadFile from FastAPI
        parent_note_id: Optional[int] = None,
        doc_type_id_form: Optional[int] = None,
        note_type_id_form: Optional[int] = None
) -> Tuple[Optional[models.Note], Optional[models.Document], Optional[str]]:
    logger.info(f"Starting file ingestion for: {file.filename}")

    # Use the UPLOAD_DIR_SERVICE_COPY defined in this file
    # Ensure unique filename in storage to avoid overwrites
    original_filename = Path(file.filename).name if file.filename else "uploaded_file"
    base_filename = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in original_filename)

    temp_saved_file_path = UPLOAD_DIR_SERVICE_COPY / base_filename
    counter = 1
    while temp_saved_file_path.exists():
        name_part, ext_part = os.path.splitext(base_filename)  # Use os.path.splitext for robustness
        temp_saved_file_path = UPLOAD_DIR_SERVICE_COPY / f"{name_part}_{counter}{ext_part}"
        counter += 1

    try:
        with open(temp_saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)  # Use shutil.copyfileobj
        logger.info(f"File '{file.filename}' temporarily saved to '{temp_saved_file_path}' for processing.")
    except Exception as e_save:
        logger.exception(f"Failed to save uploaded file '{file.filename}' for ingestion: {e_save}")
        return None, None, f"Failed to save file: {str(e_save)}"
    finally:
        file.file.close()

    extracted_text: Optional[str] = None
    if file.content_type == "text/plain":
        try:
            with open(temp_saved_file_path, "r", encoding='utf-8', errors='ignore') as f:
                extracted_text = f.read()
        except Exception as e_read:
            logger.error(f"Error reading text file {temp_saved_file_path}: {e_read}")
            extracted_text = f"Error reading file: {file.filename}"
    elif file.content_type == "application/pdf":
        logger.warning("PDF text extraction for file ingestion is not yet implemented robustly.")
        extracted_text = f"Text extraction from PDF '{file.filename}' is a placeholder. Full content of PDF."
        # Add actual PDF extraction logic here (e.g., using PyMuPDF)
    else:
        logger.warning(f"Text extraction for content type '{file.content_type}' is not yet implemented.")
        extracted_text = f"Content of file '{file.filename}'. Type '{file.content_type}' not processed for text."

    if not extracted_text:
        if temp_saved_file_path.exists(): os.remove(temp_saved_file_path)
        return None, None, "Could not extract text from file or file was empty."

    # The _persist_crawled_content helper needs the path that will be stored in the DB for the Document.
    # For uploaded files, this should be just the filename, assuming UPLOAD_DIR_SERVICE_COPY is the final storage.
    db_document_path = temp_saved_file_path.name  # This is "filename_counter.ext"

    created_note, created_doc, db_error = await _persist_crawled_content(
        db,
        url=None,  # No source URL for a file upload in this context (it's local)
        extracted_text=extracted_text,
        parent_note_id=parent_note_id,
        custom_title=Path(file.filename).stem,  # Use original filename stem as title suggestion
        document_path_for_db=db_document_path,  # Pass the filename to be stored in Document.path
        document_mime_type=file.content_type
    )

    if db_error:
        if temp_saved_file_path.exists(): os.remove(temp_saved_file_path)  # Clean up if DB persistence failed
        return None, None, db_error

    # If successful, the temp_saved_file_path IS the final path if UPLOAD_DIR_SERVICE_COPY is the final destination
    # If UPLOAD_DIR_SERVICE_COPY was truly temporary, you would now move temp_saved_file_path
    # to a permanent location and update created_doc.path if necessary.
    # For this example, we assume UPLOAD_DIR_SERVICE_COPY is the final resting place.

    return created_note, created_doc, None