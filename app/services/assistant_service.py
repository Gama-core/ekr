# app/services/assistant_service.py
import logging
from sqlalchemy.orm import Session
from typing import List, Tuple

from app import schemas, models
from app.services import llm_service
from app.services.crud import crud_note
from app.services import web_context_service
from app.services import rag_service # Keep import for structure

logger = logging.getLogger(__name__)

# Type Aliases
ContextChunk = str
SourceInfo = schemas.assistant.Source

# LLM Prompts / Config
ANSWER_WITH_CONTEXT_SYSTEM_PROMPT = """
You are a helpful AI assistant. Answer the user's question based ONLY on the following context provided.
The context may come from specific notes the user selected, notes automatically retrieved from the knowledge base via semantic search, or external web pages.
Be concise and factual. If the context does not provide enough information to answer the question, state that clearly.
Do not make up information not present in the context.
"""
MAX_COMBINED_CONTEXT_LENGTH = 4000

async def process_assistant_query(
    db: Session,
    request: schemas.assistant.AssistantQueryRequest
) -> schemas.assistant.AssistantResponse:
    # Use the new flag name in logging
    logger.info(
        f"Processing assistant query: '{request.user_query[:50]}...' "
        f"(Semantic Search: {request.use_semantic_search}, Web: {request.use_web_search}, "
        f"Selected Notes: {request.selected_note_ids})"
    )
    all_context_chunks: List[ContextChunk] = []
    all_sources: List[SourceInfo] = []

    # --- 1. Gather Context ---
    try:
        # a) From User-Selected Notes (Always fetch if provided)
        if request.selected_note_ids:
            logger.info(f"Fetching context from user-selected notes: {request.selected_note_ids}")
            for note_id in request.selected_note_ids:
                note = crud_note.get_note(db, note_id=note_id)
                if note and note.text:
                    all_context_chunks.append(f"Source: Selected Note ID {note.id} - Title: {note.title}\nContent:\n{note.text}")
                    all_sources.append(SourceInfo(type="note", id=note.id, title=note.title))
                    logger.debug(f"Added context from selected Note ID: {note.id}")
                else:
                    logger.warning(f"User-selected note ID {note_id} not found or has no text.")

        # b) From Knowledge Base via Semantic Search (RAG - Currently Stubbed)
        # Use the new flag here:
        if request.use_semantic_search:
            logger.info("Attempting knowledge base semantic search (RAG)... [CURRENTLY STUBBED]")
            # Call the stubbed RAG service
            rag_context_chunks, rag_sources = await rag_service.retrieve_context(db, request.user_query)

            if rag_context_chunks: # Will be false until RAG implemented
                 logger.info(f"Retrieved {len(rag_context_chunks)} context chunks via RAG.")
                 all_context_chunks.extend(rag_context_chunks)
                 all_sources.extend(rag_sources)
            else:
                 logger.info("No relevant context found via semantic search (RAG) [Stubbed].")

        # c) From Web Search (Using Refactored Service)
        if request.use_web_search:
            logger.info("Attempting to retrieve context from Web Search...")
            web_text, web_source, _ = await web_context_service.get_web_context_for_query(request.user_query)
            if web_text and web_source:
                logger.info(f"Retrieved web context from: {web_source.url}")
                all_context_chunks.append(f"Source: Web URL - {web_source.url}\nContent:\n{web_text}")
                all_sources.append(web_source)
            else:
                logger.warning("Failed to retrieve usable context from web search.")

    except Exception as e_context:
        logger.exception("Error during context gathering phase.")
        logger.error(f"Proceeding despite error during context gathering: {e_context}")

    # --- 2. Check if any context was found ---
    if not all_context_chunks:
        logger.warning("No context found from any enabled source.")
        # Update fallback message generation
        attempted_sources = []
        if request.selected_note_ids: attempted_sources.append("your selected notes")
        # Check the new flag:
        if request.use_semantic_search: attempted_sources.append("the knowledge base via semantic search (currently stubbed)")
        if request.use_web_search: attempted_sources.append("the web")

        if not attempted_sources:
             final_answer = "No information sources were requested to answer the query."
        else:
            sources_str = " or ".join(attempted_sources)
            final_answer = f"I couldn't find relevant information from {sources_str} to answer your question."

        return schemas.assistant.AssistantResponse(
            answer=final_answer, sources=[], conversation_id=request.conversation_id
        )

    # --- 3. Prepare Combined Context for LLM ---
    combined_context = "\n\n---\n\n".join(all_context_chunks)
    if len(combined_context) > MAX_COMBINED_CONTEXT_LENGTH:
        logger.warning(f"Combined context ({len(combined_context)} chars) exceeds limit ({MAX_COMBINED_CONTEXT_LENGTH}). Truncating.")
        combined_context = combined_context[:MAX_COMBINED_CONTEXT_LENGTH] + "\n... [Context Truncated]"

    # --- 4. Generate Final Answer using LLM ---
    user_prompt = f"CONTEXT:\n\"\"\"\n{combined_context}\n\"\"\"\n\nUSER QUESTION: {request.user_query}"
    logger.debug(f"Sending combined context (approx {len(combined_context)} chars) and query to LLM.")
    final_answer = await llm_service.generate_llm_response(
        system_prompt=ANSWER_WITH_CONTEXT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=500, temperature=0.5
    )
    if not final_answer or "Error:" in final_answer:
         logger.error(f"LLM failed to generate final answer. Response: {final_answer}")
         final_answer = "I gathered information but encountered an issue while formulating the final answer."

    # --- 5. Return Response ---
    unique_sources_dict = {}
    for s in all_sources:
        key = f"{s.type}:{s.id or s.url}"
        if key not in unique_sources_dict:
             unique_sources_dict[key] = s
    unique_sources = list(unique_sources_dict.values())
    logger.info(f"Generated final answer (approx {len(final_answer or '')} chars) using {len(unique_sources)} unique sources.")
    return schemas.assistant.AssistantResponse(
        answer=final_answer.strip() if final_answer else "Error generating answer.",
        sources=unique_sources,
        conversation_id=request.conversation_id
    )