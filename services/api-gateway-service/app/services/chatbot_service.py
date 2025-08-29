# app/services/chatbot_service.py
import logging
import asyncio
from typing import Optional, List


from .. import clients
from ..schemas import chatbot_schemas

logger = logging.getLogger(__name__)


async def process_rag_chat_request(request: chatbot_schemas.ChatRequest) -> chatbot_schemas.ChatResponse:
    """
    Orchestrates the RAG workflow for the chatbot.
    """
    logger.info(f"Processing RAG chat request for user {request.user_id}.")

    # --- 1. RETRIEVE PHASE ---
    retrieved_items = await clients.semantic_retrieval_client.retrieve_context(
        query=request.query, user_id=request.user_id
    )

    # --- 2. SYNTHESIZE PHASE ---
    system_prompt = (
        "You are a helpful AI assistant. Your task is to answer the user's question based on the provided conversation history "
        "and the context from their personal notes. If the context does not contain the answer, state that you couldn't find "
        "the information in their notes. Cite the note title when you use information from a source document."
    )

    # Format the retrieved context for the LLM
    context_str = "No relevant notes found."
    if retrieved_items:
        context_parts = ["--- CONTEXT FROM YOUR NOTES ---"]
        for item in retrieved_items:
            context_parts.append(f"Note Title: {item.get('title', 'Untitled')}\nContent: {item.get('text_chunk', '')}")
        context_str = "\n\n".join(context_parts)

    # Flatten history and new query into a single user prompt
    prompt_parts = [context_str]
    if request.history:
        prompt_parts.append("\n--- CONVERSATION HISTORY ---")
        for message in request.history:
            prompt_parts.append(f"{message.role.capitalize()}: {message.content}")

    prompt_parts.append(f"\nNew Question: {request.query}")
    user_prompt = "\n".join(prompt_parts)

    # Call the LLM
    llm_payload = {"user_prompt": user_prompt, "system_prompt": system_prompt}
    llm_response = await clients.llm_query_client.query_llm(llm_payload)

    # --- 3. RESPOND PHASE ---
    # Create the list of source objects for the frontend
    sources = [
        chatbot_schemas.Source(
            type="note",
            title=item.get('title', 'Untitled'),
            note_id=item.get('note_id', 0),
            content_snippet=item.get('text_chunk', '')
        ) for item in retrieved_items
    ]

    return chatbot_schemas.ChatResponse(
        answer=llm_response.get("response_text", "I'm sorry, I couldn't generate a response.").strip(),
        sources=sources
    )


async def process_chat_request(
        request: chatbot_schemas.ChatRequest,
        files: Optional[List[chatbot_schemas.FileData]] = None
) -> chatbot_schemas.ChatResponse:
    """
    Orchestrates the full chat workflow: RAG, optional OCR, optional Web Search, and Synthesis.
    It gathers context from multiple sources in parallel before synthesizing an answer.
    """
    file_count = len(files) if files else 0
    logger.info(
        f"Processing chat request for user {request.user_id}. Files: {file_count}, Web Search: {request.web_search_enabled}")

    # --- 1. GATHER CONTEXT PHASE (in parallel) ---
    tasks = []

    # Task 1: Always retrieve context from user's notes (RAG).
    rag_task = asyncio.create_task(
        clients.semantic_retrieval_client.retrieve_context(query=request.query, user_id=request.user_id)
    )
    tasks.append(rag_task)

    # Task 2: Create an OCR processing task for each uploaded file.
    if files:
        for file_data in files:
            ocr_task = asyncio.create_task(clients.ocr_client.process_uploaded_file(file_data))
            tasks.append(ocr_task)

    # Task 3: Conditionally create the full web search task (Rewrite -> Search -> Crawl).
    if request.web_search_enabled:
        async def perform_web_search_task():
            # Step 3a: Rewrite the query
            rewritten_query = await _rewrite_query_for_web_search(request)
            # Step 3b: Perform Google search with the new query
            google_results = await clients.google_search_client.perform_search(rewritten_query)
            # Step 3c: Crawl the top URLs
            urls_to_crawl = [result.get("link") for result in google_results if result.get("link")]
            crawled_pages = await clients.web_crawl_client.crawl_urls(urls_to_crawl)
            return crawled_pages

        web_search_task = asyncio.create_task(perform_web_search_task())
        tasks.append(web_search_task)

    # Wait for all context-gathering tasks to complete concurrently.
    results = await asyncio.gather(*tasks)

    # --- PARSE GATHERED RESULTS ---
    # Carefully map the results from asyncio.gather back to their sources.
    retrieved_items = results[0]

    ocr_results_start_index = 1
    if files:
        ocr_results_end_index = ocr_results_start_index + len(files)
        ocr_results = results[ocr_results_start_index:ocr_results_end_index]
    else:
        ocr_results = []

    web_search_results = results[-1] if request.web_search_enabled else []

    # --- 2. SYNTHESIZE PHASE ---
    system_prompt = (
        "You are a helpful AI assistant. Your task is to answer the user's question by synthesizing information from all provided context. "
        "The context may come from the user's personal notes, from documents they uploaded, or from web search results. "
        "If the context does not contain the answer, state that you couldn't find the information. "
        "Cite your sources (note title, file name, or web page title) when you use information from them."
    )

    context_parts = []
    sources: List[chatbot_schemas.Source] = []

    # Add context and sources from RAG (personal notes).
    if retrieved_items:
        context_parts.append("--- CONTEXT FROM YOUR NOTES ---")
        for item in retrieved_items:
            sources.append(chatbot_schemas.Source(
                type="note",
                title=item.get('title', 'Untitled'),
                note_id=item.get('note_id', 0),
                content_snippet=item.get('text_chunk', '')
            ))
            context_parts.append(f"Note Title: {item.get('title', 'Untitled')}\nContent: {item.get('text_chunk', '')}")

    # Add context and sources from OCR (uploaded files).
    if files and ocr_results:
        for i, ocr_text in enumerate(ocr_results):
            file_data = files[i]
            if ocr_text and file_data.filename:
                sources.append(chatbot_schemas.Source(
                    type="file",
                    title=file_data.filename,
                    content_snippet=ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text
                ))
                context_parts.append(f"--- CONTEXT FROM UPLOADED FILE: {file_data.filename} ---")
                context_parts.append(ocr_text)

    # Add context and sources from Web Search.
    if web_search_results:
        context_parts.append("--- CONTEXT FROM WEB SEARCH ---")
        for page in web_search_results:
            if page.get("status") == "success":
                title = page.get('title', 'Untitled Web Page')
                content = page.get('content_markdown', '')
                sources.append(chatbot_schemas.Source(
                    type="file",  # Represent web pages as external 'file' sources
                    title=title,
                    content_snippet=content[:500] + "..." if len(content) > 500 else content
                ))
                # Truncate long web pages to fit within the context window
                context_parts.append(f"Web Page Title: {title}\nContent: {content[:2000]}")

    context_str = "\n\n".join(context_parts) if context_parts else "No context was found."

    # Build the final user prompt including context, history, and the new question.
    prompt_parts = [context_str]
    if request.history:
        prompt_parts.append("\n--- CONVERSATION HISTORY ---")
        for message in request.history:
            prompt_parts.append(f"{message.role.capitalize()}: {message.content}")

    prompt_parts.append(f"\nNew Question: {request.query}")
    user_prompt = "\n".join(prompt_parts)

    # Call the LLM with the complete prompt.
    llm_payload = {"user_prompt": user_prompt, "system_prompt": system_prompt}
    llm_response = await clients.llm_query_client.query_llm(llm_payload)

    # --- 3. RESPOND PHASE ---
    return chatbot_schemas.ChatResponse(
        answer=llm_response.get("response_text", "I'm sorry, I couldn't generate a response.").strip(),
        sources=sources
    )


async def _rewrite_query_for_web_search(request: chatbot_schemas.ChatRequest) -> str:
    """
    Uses an LLM to rewrite a conversational query into a keyword-based search query.
    If there is no conversation history, it returns the original query.
    """
    # If there's no history, the user's query is likely already a good search query.
    if not request.history:
        return request.query

    logger.info("Rewriting user query for web search...")

    # Prompt engineering for the rewrite task.
    system_prompt = (
        "You are an expert at rewriting conversational questions into high-quality, keyword-based Google search queries. "
        "Your response must be ONLY the rewritten search query and nothing else. Do not add any conversational text, explanations, or quotes."
    )

    # Format the history into a simple string for the prompt.
    history_str = "\n".join([f"{msg.role.capitalize()}: {msg.content}" for msg in request.history])

    user_prompt = (
        "Based on the following conversation history, rewrite the 'Latest Question' into a concise Google search query.\n\n"
        f"--- CONVERSATION HISTORY ---\n{history_str}\n--- END OF HISTORY ---\n\n"
        f"Latest Question: {request.query}"
    )

    llm_payload = {"user_prompt": user_prompt, "system_prompt": system_prompt}

    try:
        llm_response = await clients.llm_query_client.query_llm(llm_payload)
        rewritten_query = llm_response.get("response_text", "").strip().replace("\"", "")

        # Basic validation: ensure the LLM didn't add extra conversational text.
        if "\n" not in rewritten_query and rewritten_query:
            logger.info(f"Original query: '{request.query}' -> Rewritten query: '{rewritten_query}'")
            return rewritten_query
        else:
            # Handle cases where the LLM might still respond with conversational text.
            logger.warning(
                f"LLM rewrite response was not a clean query, falling back to original. Response: '{rewritten_query}'")
            return request.query

    except Exception as e:
        logger.error(f"Failed to rewrite query due to an exception, falling back to original. Error: {e}")

    # Fallback to the original query if rewriting fails for any reason.
    return request.query