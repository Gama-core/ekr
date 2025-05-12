# app/services/ingestion_service.py
import logging
import asyncio
from typing import Optional, List

from sqlalchemy.orm import Session
from app import schemas, models
from app.services import google_search, web_crawler, llm_service
from app.services.crud import (
    crud_document, crud_document_type,
    crud_note, crud_note_type,
    crud_note_document
)
from app.core.config import settings
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig
from playwright.async_api import Error as PlaywrightError

logger = logging.getLogger(__name__)

# Define constants for clarity or import from a config
# This should match the max_length constraint in your schemas.NoteBase.text
NOTE_TEXT_MAX_LENGTH_FOR_SCHEMA = 4000

# --- Helper function to create Note title (can be improved) ---
async def generate_title_for_content(url: str, text_content: Optional[str]) -> str:
    if not text_content:
        return url.split('/')[-1] or url.split('/')[-2] or "Ingested Content from " + url

    try:
        prompt = f"Generate a concise, descriptive title (max 10 words) for the following web page content scraped from {url}:\n\nCONTEXT抜粋:\n{text_content[:1500]}\n\nTITLE:" # Use up to 1500 chars of text_content
        title = await llm_service.generate_llm_response(
            system_prompt="You are a title generation assistant.",
            user_prompt=prompt,
            max_tokens=30,
            temperature=0.3
        )
        if title and "Error:" not in title:
            return title.strip().strip('"')
    except Exception as e:
        logger.error(f"LLM title generation failed for {url}: {e}")

    # Fallback if LLM fails
    first_sentence = text_content.split('.')[0]
    return (first_sentence[:100] + '...') if len(first_sentence) > 100 else first_sentence


async def process_search_and_crawl(
    db: Session,
    request: schemas.ingestion.IngestionRequest
) -> schemas.ingestion.IngestionResponse:
    """
    Performs web search, crawls URLs, extracts text, and saves
    results as Note and Document entries in the database.
    """
    logger.info(f"Starting ingestion process for query: '{request.query}', num_results: {request.num_results}")
    processed_urls_results: List[schemas.ingestion.ProcessedUrlResult] = []

    # 1. Search for URLs
    try:
        urls_to_process = await google_search.search_web(query=request.query, num_results=request.num_results)
        if not urls_to_process:
            logger.warning(f"No URLs found via Google Search for query: '{request.query}'")
            return schemas.ingestion.IngestionResponse(
                message="No URLs found for the search query.",
                processed_urls=[]
            )
        logger.info(f"Found {len(urls_to_process)} URLs to process: {urls_to_process}")
    except Exception as e_search:
        logger.exception(f"Error during Google Search for query '{request.query}'")
        return schemas.ingestion.IngestionResponse(
             message=f"Failed during web search: {str(e_search)}", # Use str(e_search)
             processed_urls=[]
        )

    # 2. Process each URL
    for target_url in urls_to_process:
        current_result = schemas.ingestion.ProcessedUrlResult(url=target_url, status="pending")
        extracted_text: Optional[str] = None # This will hold the full crawled text
        crawl_error: Optional[str] = None

        # 2a. Crawl the URL
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
                logger.warning(f"No usable content extracted from {target_url}")
                crawl_error = "No usable content extracted"
            else:
                 logger.info(f"Successfully extracted ~{len(extracted_text)} chars from {target_url}")
        except asyncio.TimeoutError:
             logger.error(f"Crawl timed out after {timeout_seconds}s for URL: {target_url}")
             crawl_error = f"Crawl timed out ({timeout_seconds}s)"
        except PlaywrightError as pe:
            logger.error(f"PlaywrightError ({type(pe).__name__}) crawling {target_url}: {str(pe)}")
            crawl_error = f"Playwright Error: {type(pe).__name__}"
        except Exception as e_crawl:
            logger.exception(f"Unexpected error crawling {target_url}")
            crawl_error = f"Unexpected crawl error: {type(e_crawl).__name__}"

        if crawl_error:
            current_result.status = "crawl_failed"
            current_result.error = crawl_error
            processed_urls_results.append(current_result)
            continue

        # 2b. Persist to Database (if crawl succeeded and extracted_text is not None)
        if extracted_text:
            try:
                doc_type = crud_document_type.get_or_create_document_type(db, name="Crawled Web Page")
                note_type = crud_note_type.get_or_create_note_type(db, name="Ingested Web Content")

                doc_schema = schemas.DocumentCreate(
                    doc_type_id=doc_type.id,
                    comment=f"Content ingested from web crawl of {target_url}",
                    mime_type="text/markdown",
                    url=target_url,
                    path=target_url,
                    name= target_url.split('/')[-1] or f"Document for {target_url}"
                )
                created_document = crud_document.create_document(db=db, doc_in=doc_schema)
                logger.info(f"Created Document ID: {created_document.id} for URL: {target_url}")

                # --- TRUNCATE TEXT FOR THE NOTE SCHEMA ---
                text_for_note_schema: str # Explicitly type hint
                if len(extracted_text) > NOTE_TEXT_MAX_LENGTH_FOR_SCHEMA:
                    logger.warning(
                        f"Extracted text for Note ({len(extracted_text)} chars) exceeds max length ({NOTE_TEXT_MAX_LENGTH_FOR_SCHEMA}). Truncating."
                    )
                    text_for_note_schema = extracted_text[:NOTE_TEXT_MAX_LENGTH_FOR_SCHEMA]
                else:
                    text_for_note_schema = extracted_text
                # --- END TRUNCATION ---

                # Generate title using the (potentially truncated) text for the note
                note_title = await generate_title_for_content(target_url, text_for_note_schema)

                # Create Note entry USING THE (POTENTIALLY) TRUNCATED TEXT
                note_schema = schemas.NoteCreate(
                    title=note_title,
                    text=text_for_note_schema,  # <--- THIS IS THE FIX: Use the truncated version
                    type_id=note_type.id,
                )
                created_note = crud_note.create_note(db=db, note_in=note_schema, owner_id=settings.SYSTEM_USER_ID)
                logger.info(f"Created Note ID: {created_note.id} for URL: {target_url}")

                crud_note_document.create_note_document_link(
                    db=db, note_id=created_note.id, document_id=created_document.id
                )
                logger.info(f"Linked Note ID {created_note.id} and Document ID {created_document.id}")

                current_result.status = "success"
                current_result.note_id = created_note.id
                current_result.document_id = created_document.id

            except Exception as e_db:
                logger.exception(f"Database error during persistence for URL {target_url}")
                current_result.status = "db_error"
                current_result.error = f"DB Error: {type(e_db).__name__} - {str(e_db)}" # Add error message
        else:
             # This case should ideally be caught by crawl_error check, but good for robustness
             logger.warning(f"Extracted text was None for URL {target_url}, skipping DB persistence.")
             current_result.status = "crawl_failed" # Or a new status like "no_content_to_persist"
             current_result.error = "No content extracted from URL to persist."

        processed_urls_results.append(current_result)

    final_message = f"Ingestion process completed for query '{request.query}'. Processed {len(processed_urls_results)} URLs."
    logger.info(final_message)
    return schemas.ingestion.IngestionResponse(
        message=final_message,
        processed_urls=processed_urls_results
    )