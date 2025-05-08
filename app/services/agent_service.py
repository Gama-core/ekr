# app/services/agent_service.py
import logging
from app import schemas
from app.services import google_search
from app.services import llm_service

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig
from app.services.web_crawler import crawl_and_extract_with_instance
from playwright.async_api import Error as PlaywrightError  # Import base PlaywrightError

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
MAX_URLS_TO_TRY = 5  # Number of URLs to attempt crawling from search results


async def process_user_query_with_web_context(
        user_query: str
) -> schemas.agent.AgentResponse:
    logger.info(f"Processing user query: '{user_query}'")
    intermediate_steps: list[schemas.agent.AgentStep] = []
    final_answer_str = "Could not process the query."
    crawled_url_for_response = None
    crawled_text = None  # This will hold the first successfully crawled content

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
            details=f"LLM generated search query: '{generated_search_query}'" if generated_search_query and "Error" not in generated_search_query else f"Failed to generate search query. LLM Response: {generated_search_query}"
        ))

        if not generated_search_query or "Error" in generated_search_query:
            logger.error(f"LLM failed to generate a search query. Response: {generated_search_query}")
            final_answer_str = "I had trouble understanding what to search for. Please try rephrasing your question."
            return schemas.agent.AgentResponse(final_answer=final_answer_str, intermediate_steps=intermediate_steps)

        # Step 2: Web Search - Request more URLs
        urls_found = await google_search.search_web(query=generated_search_query, num_results=MAX_URLS_TO_TRY)
        intermediate_steps.append(schemas.agent.AgentStep(
            step_name="Web Search",
            details=f"Found {len(urls_found)} URLs: {urls_found}" if urls_found else f"No URLs found for '{generated_search_query}'"
        ))

        if not urls_found:
            logger.warning(f"No URLs found for search query: '{generated_search_query}'")
            final_answer_str = f"I couldn't find relevant web pages for the search term: '{generated_search_query}'."
            return schemas.agent.AgentResponse(final_answer=final_answer_str, intermediate_steps=intermediate_steps)

        # Step 3: Web Crawl - Loop through URLs and attempt to crawl
        successful_crawl = False
        for i, target_url in enumerate(urls_found):
            if i >= MAX_URLS_TO_TRY:  # Safety break, though search_web should limit
                break

            logger.info(f"Attempting to crawl URL {i + 1}/{len(urls_found)}: {target_url}")
            current_crawl_step_details = []
            try:
                browser_cfg_for_crawl = BrowserConfig(headless=True, verbose=False)
                async with AsyncWebCrawler(config=browser_cfg_for_crawl) as crawler:
                    logger.info(f"Temporary AsyncWebCrawler instance created for {target_url}")
                    # Ensure the instance is passed correctly
                    temp_crawled_text = await crawl_and_extract_with_instance(
                        crawler_instance=crawler,  # Pass the created crawler instance
                        url=target_url
                    )
                    logger.info(f"Temporary AsyncWebCrawler instance for {target_url} will be closed.")

                if temp_crawled_text:
                    crawled_text = temp_crawled_text
                    crawled_url_for_response = target_url
                    successful_crawl = True
                    current_crawl_step_details.append(
                        f"Successfully crawled and extracted content from {target_url} (approx {len(crawled_text)} chars).")
                    logger.info(f"Successfully crawled {target_url}")
                    break  # Exit loop on first successful crawl
                else:
                    current_crawl_step_details.append(
                        f"Crawl attempt for {target_url} completed but no usable content extracted.")
                    logger.warning(f"No usable content extracted from {target_url}")

            except PlaywrightError as pe:  # Catch Playwright-specific errors like TargetClosedError
                error_detail = f"PlaywrightError ({type(pe).__name__}) while crawling {target_url}: {str(pe)}"
                current_crawl_step_details.append(error_detail)
                logger.error(error_detail)
            except Exception as e_crawl:  # Catch other unexpected errors during this specific crawl
                error_detail = f"Unexpected error ({type(e_crawl).__name__}) while crawling {target_url}: {str(e_crawl)}"
                current_crawl_step_details.append(error_detail)
                logger.exception(f"Unexpected error crawling {target_url}")  # Log full traceback for this crawl error

            finally:  # Add step details for this attempt regardless of outcome
                intermediate_steps.append(schemas.agent.AgentStep(
                    step_name=f"Web Crawl Attempt {i + 1}",
                    details=" | ".join(
                        current_crawl_step_details) if current_crawl_step_details else f"Attempted crawl for {target_url}, no specific details."
                ))

        if not successful_crawl:
            logger.error(f"Failed to crawl or extract usable content from any of the {len(urls_found)} URLs found.")
            final_answer_str = f"I found some web pages for '{generated_search_query}', but had trouble reading their content after trying multiple sources."
            # Proceed to LLM, which should handle empty context if crawled_text is still None
        elif crawled_text and len(crawled_text) > MAX_CONTEXT_LENGTH:  # crawled_text is guaranteed to be non-None here
            logger.info(
                f"Truncating crawled context from {len(crawled_text)} to {MAX_CONTEXT_LENGTH} chars for URL {crawled_url_for_response}.")
            crawled_text = crawled_text[:MAX_CONTEXT_LENGTH]

        # Step 4: LLM - Answer Generation with Context
        context_for_llm = crawled_text if crawled_text else "No specific content could be extracted from any of the attempted web pages."
        answer_prompt = f"User's original question: \"{user_query}\"\n\nWeb page context from {crawled_url_for_response or 'N/A'}:\n\"\"\"\n{context_for_llm}\n\"\"\""

        llm_final_answer = await llm_service.generate_llm_response(
            system_prompt=ANSWER_WITH_CONTEXT_SYSTEM_PROMPT,
            user_prompt=answer_prompt,
            max_tokens=500,
            temperature=0.5
        )
        intermediate_steps.append(schemas.agent.AgentStep(
            step_name="Generate Final Answer",
            details="LLM generated the final answer." if llm_final_answer and "Error" not in llm_final_answer else f"LLM failed to generate a final answer. LLM Response: {llm_final_answer}"
        ))

        if not llm_final_answer or "Error" in llm_final_answer:
            logger.error(f"LLM failed to generate a final answer using the context. Response: {llm_final_answer}")
            if crawled_text:  # We had some context
                final_answer_str = f"I retrieved information from {crawled_url_for_response} but encountered an issue formulating a concise answer. You might want to check the source ({crawled_url_for_response}) directly."
            else:  # No context was successfully retrieved
                final_answer_str = f"I found search results for '{generated_search_query}' but couldn't retrieve content from them. Then, I had an issue formulating an answer."
        else:
            final_answer_str = llm_final_answer

    except Exception as e_main:  # Main try-except for the whole process
        # This will catch errors outside the crawl loop or if the loop itself has an unhandled issue
        logger.exception("Unhandled exception in process_user_query_with_web_context")
        intermediate_steps.append(
            schemas.agent.AgentStep(step_name="Critical Error", details=f"{type(e_main).__name__}: {str(e_main)}"))
        final_answer_str = "A critical error occurred while processing your request. Please try again later."

    logger.info(f"Final answer for query '{user_query}': '{final_answer_str[:100]}...'")
    return schemas.agent.AgentResponse(
        final_answer=final_answer_str,
        intermediate_steps=intermediate_steps,
        source_url_crawled=crawled_url_for_response  # This will be the URL of the successfully crawled page
    )