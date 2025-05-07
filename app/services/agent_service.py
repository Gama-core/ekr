# app/services/agent_service.py
import logging
from app import schemas
from app.services import google_search  # web_crawler is now used differently
from app.services import llm_service

# --- Import crawler and config classes directly ---
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig
# --- Import the modified crawl function ---
from app.services.web_crawler import crawl_and_extract_with_instance

logger = logging.getLogger(__name__)

SEARCH_QUERY_GENERATION_SYSTEM_PROMPT = """
You are an expert search query formulator.
Based on the user's question, generate a concise and effective Google search query
that will help find the most relevant web page to answer it.
Return ONLY the search query, nothing else.
"""

ANSWER_WITH_CONTEXT_SYSTEM_PROMPT = """
You are a helpful AI assistant.
Answer the user's original question based on the provided web page context.
Provide a short, direct, and concise answer.
If the context does not provide enough information to answer the question,
state that you couldn't find a definitive answer in the provided context.
Do not make up information.
"""
MAX_CONTEXT_LENGTH = 3500


async def process_user_query_with_web_context(
        user_query: str
) -> schemas.agent.AgentResponse:
    logger.info(f"Processing user query: '{user_query}'")
    intermediate_steps: list[schemas.agent.AgentStep] = []
    final_answer_str = "Could not process the query."
    crawled_url_for_response = None
    crawled_text = None  # Initialize crawled_text

    try:
        # Step 1: LLM - Generate Search Query
        search_query_prompt = f"User's original question: \"{user_query}\""
        generated_search_query = await llm_service.generate_llm_response(
            system_prompt=SEARCH_QUERY_GENERATION_SYSTEM_PROMPT,
            user_prompt=search_query_prompt,
            max_tokens=60,
            temperature=0.2
        )
        intermediate_steps.append(schemas.agent.AgentStep(
            step_name="Generate Search Query",
            details=f"LLM generated search query: '{generated_search_query}'" if generated_search_query else "Failed to generate search query."
        ))

        if not generated_search_query or "Error" in generated_search_query:
            logger.error(f"LLM failed to generate a search query. Response: {generated_search_query}")
            final_answer_str = "I had trouble understanding what to search for. Please try rephrasing your question."
            return schemas.agent.AgentResponse(final_answer=final_answer_str, intermediate_steps=intermediate_steps)

        # Step 2: Web Search
        urls_found = await google_search.search_web(query=generated_search_query, num_results=1)
        intermediate_steps.append(schemas.agent.AgentStep(
            step_name="Web Search",
            details=f"Found URLs: {urls_found}" if urls_found else f"No URLs found for '{generated_search_query}'"
        ))

        if not urls_found:
            logger.warning(f"No URLs found for search query: '{generated_search_query}'")
            final_answer_str = f"I couldn't find relevant web pages for the search term: '{generated_search_query}'."
            return schemas.agent.AgentResponse(final_answer=final_answer_str, intermediate_steps=intermediate_steps)

        target_url = urls_found[0]
        crawled_url_for_response = target_url
        logger.info(f"Selected URL to crawl: {target_url}")

        # --- Step 3: Web Crawl ---
        # Configure and create a new crawler instance for this specific crawl operation
        # Match the headless=False, verbose=True from your successful standalone test for debugging
        # For production, you'd likely use headless=True, verbose=False (or based on config)
        browser_cfg_for_crawl = BrowserConfig(headless=False, verbose=True)
        async with AsyncWebCrawler(config=browser_cfg_for_crawl) as crawler:
            logger.info(f"Temporary AsyncWebCrawler instance created for {target_url}")
            crawled_text = await crawl_and_extract_with_instance(
                crawler_instance=crawler,
                url=target_url
                # use_simplified_config=True # Uncomment this to test with simplified config
            )
            logger.info(f"Temporary AsyncWebCrawler instance for {target_url} will be closed.")
        # The 'async with' block ensures crawler.close() is called.

        intermediate_steps.append(schemas.agent.AgentStep(
            step_name="Web Crawl",
            details=f"Crawled content from {target_url} (approx {len(crawled_text or '')} chars)" if crawled_text else f"Failed to crawl {target_url}"
        ))

        if not crawled_text:
            logger.error(f"Failed to crawl or extract content from {target_url}")
            final_answer_str = f"I found a page ({target_url}) but had trouble reading its content."
            # No 'return' here yet, will fall through to final answer generation
            # which should handle the case where crawled_text is None.
        else:  # Only truncate if crawled_text is not None
            if len(crawled_text) > MAX_CONTEXT_LENGTH:
                logger.info(f"Truncating crawled context from {len(crawled_text)} to {MAX_CONTEXT_LENGTH} chars.")
                crawled_text = crawled_text[:MAX_CONTEXT_LENGTH]

        # --- Step 4: LLM - Answer Generation with Context ---
        # Ensure crawled_text is a string, even if empty, to avoid issues with prompt formatting.
        # The LLM should be prompted to handle cases where context might be missing or insufficient.
        context_for_llm = crawled_text if crawled_text else "No specific content could be extracted from the web page."
        answer_prompt = f"User's original question: \"{user_query}\"\n\nWeb page context from {target_url}:\n\"\"\"\n{context_for_llm}\n\"\"\""

        llm_final_answer = await llm_service.generate_llm_response(
            system_prompt=ANSWER_WITH_CONTEXT_SYSTEM_PROMPT,
            user_prompt=answer_prompt,
            max_tokens=500,
            temperature=0.5
        )
        intermediate_steps.append(schemas.agent.AgentStep(
            step_name="Generate Final Answer",
            details="LLM generated the final answer." if llm_final_answer and "Error" not in llm_final_answer else f"LLM failed to generate a final answer. Response: {llm_final_answer}"
        ))

        if not llm_final_answer or "Error" in llm_final_answer:
            logger.error(f"LLM failed to generate a final answer using the context. Response: {llm_final_answer}")
            if crawled_text:  # If we had some context
                final_answer_str = f"I retrieved some information from {target_url} but had trouble formulating a concise answer. You might want to check the source directly."
            else:  # If crawl failed and we sent "No specific content..."
                final_answer_str = f"I attempted to get information from {target_url} but couldn't read the content or formulate an answer based on it."
        else:
            final_answer_str = llm_final_answer

    except Exception as e:
        logger.exception("Unhandled exception in process_user_query_with_web_context")
        intermediate_steps.append(schemas.agent.AgentStep(step_name="Critical Error", details=str(e)))
        final_answer_str = "A critical error occurred while processing your request."

    logger.info(f"Final answer for query '{user_query}': '{final_answer_str[:100]}...'")
    return schemas.agent.AgentResponse(
        final_answer=final_answer_str,
        intermediate_steps=intermediate_steps,
        source_url_crawled=crawled_url_for_response
    )