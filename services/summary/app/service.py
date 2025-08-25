import logging
import httpx
from urllib.parse import urljoin

from .config import settings
from .schemas import SummaryRequest, SummaryResponse, LLMQueryResponse

logger = logging.getLogger(__name__)

def _construct_llm_prompt(request: SummaryRequest) -> tuple[str, str]:
    """
    Constructs the system and user prompts for the LLM based on the summary request.
    For the "root_only" strategy, it explicitly ignores sub-notes.
    """
    system_prompt = (
        "You are a highly skilled summarization engine. Your task is to analyze the provided text "
        "and generate a clear, concise, and accurate summary. Do not add any conversational "
        "fluff or introductory phrases like 'Here is the summary:'. Respond ONLY with the summary text itself."
    )

    # --- KEY LOGIC for "root_only" strategy ---
    # Combine only the top-level title and text for the LLM.
    content_to_summarize = (
        f"Title: {request.note_data.title}\n\n"
        f"Content:\n{request.note_data.text_content or 'No content provided.'}"
    )

    # Create instructions for the desired level of detail.
    level_instructions = {
        "short": "The summary should be a single, highly concise sentence.",
        "medium": "The summary should be a short paragraph, approximately 3-4 sentences long.",
        "detailed": "The summary should be comprehensive, covering the main topic and key points in a detailed paragraph."
    }

    user_prompt = (
        f"Please generate a summary for the following text. {level_instructions[request.summary_level]}\n\n"
        f"--- TEXT TO SUMMARIZE ---\n"
        f"{content_to_summarize}\n"
        f"--- END OF TEXT ---"
    )

    return system_prompt, user_prompt

async def _call_llm_service(payload: dict) -> LLMQueryResponse:
    """Helper function to call the LLM Query microservice."""
    llm_service_url = urljoin(str(settings.LLM_QUERY_SERVICE_URL), "query")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(llm_service_url, json=payload, timeout=60.0)
            response.raise_for_status()
            return LLMQueryResponse(**response.json())
        except httpx.HTTPStatusError as e:
            downstream_error = e.response.text
            logger.error(f"LLM Query Service returned an error: {e.response.status_code} - {downstream_error}")
            return LLMQueryResponse(error_message=f"LLM Service Error: {downstream_error}")
        except httpx.RequestError as e:
            logger.error(f"Could not connect to LLM Query Service at {llm_service_url}: {e}")
            return LLMQueryResponse(error_message=f"Could not connect to dependent LLM Service: {e}")

async def generate_summary(request: SummaryRequest) -> SummaryResponse:
    """
    Generates a summary by preparing a prompt and calling the LLM Query service.
    """
    system_prompt, user_prompt = _construct_llm_prompt(request)

    llm_payload = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt,
        "max_tokens": settings.SUMMARY_DEFAULT_MAX_TOKENS,
    }

    try:
        llm_response = await _call_llm_service(llm_payload)

        # Prepare a base response object to avoid repetition
        base_response_args = {
            "level_used": request.summary_level,
            "strategy_used": request.summary_strategy,
            "model_used": llm_response.model_used
        }

        if llm_response.error_message:
            return SummaryResponse(**base_response_args, error_message=llm_response.error_message)

        if not llm_response.response_text:
            return SummaryResponse(**base_response_args, error_message="LLM service returned an empty response.")

        return SummaryResponse(
            **base_response_args,
            summary_text=llm_response.response_text.strip()
        )

    except Exception as e:
        logger.exception(f"Unexpected error in summary generation service: {e}")
        return SummaryResponse(
            level_used=request.summary_level,
            strategy_used=request.summary_strategy,
            error_message=f"An unexpected server error occurred: {e}"
        )