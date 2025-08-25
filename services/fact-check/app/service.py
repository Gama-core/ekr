import logging
import json
import httpx
from urllib.parse import urljoin

from .config import settings
from .schemas import FactCheckRequest, FactCheckResponse, LLMQueryResponse, NoteData, Correction

logger = logging.getLogger(__name__)


def _flatten_note_content(note: NoteData) -> str:
    """
    Recursively traverses a note and its sub-notes to generate a single,
    structured block of text with clear ID markers for the LLM.
    """
    content_parts = []

    # Create a distinct, parsable block for each note
    note_block = (
        f"--- NOTE START (ID: {note.note_id}) ---\n"
        f"Title: {note.title}\n"
        f"Content: {note.text_content or ''}\n"
        f"--- NOTE END (ID: {note.note_id}) ---"
    )
    content_parts.append(note_block)

    # Recursively add content from sub-notes
    if note.sub_notes:
        for sub_note in note.sub_notes:
            content_parts.append(_flatten_note_content(sub_note))

    return "\n\n".join(content_parts)


def _construct_llm_prompt(text_content: str) -> tuple[str, str]:
    """
    Constructs the detailed system and user prompts for the LLM,
    instructing it to use the embedded note IDs.
    """
    # Define the required JSON structure for the LLM's response, now including note_id
    json_schema = {
        "corrections": [
            {
                "note_id": "The integer ID from the 'NOTE START' block where the error was found.",
                "inaccurate_quote": "The exact text of the inaccurate statement from the document.",
                "issue": "A brief, one-sentence description of the error (e.g., 'Incorrect date', 'Misattributed quote').",
                "suggested_correction": "A revised version of the statement that is factually accurate."
            }
        ]
    }

    system_prompt = (
        "You are an expert fact-checking editor. Your task is to analyze the user's text, which is structured into blocks, "
        "identify statements that are factually inaccurate, and provide a suggested correction for each error.\n\n"
        "The user's text is formatted into blocks like this:\n"
        "--- NOTE START (ID: 123) ---\n"
        "...\n"
        "--- NOTE END (ID: 123) ---\n\n"
        "You MUST adhere to the following rules:\n"
        "1. Respond ONLY with a single, valid JSON object.\n"
        "2. Do not include any preamble, explanations, or text outside of the JSON structure.\n"
        "3. When you find an inaccuracy, you MUST include the `note_id` from the corresponding `NOTE START` block in your JSON response.\n"
        "4. If no inaccuracies are found, respond with an empty list for the 'corrections' field.\n\n"
        f"The JSON response must follow this exact schema:\n{json.dumps(json_schema, indent=2)}"
    )

    user_prompt = (
        "Please analyze the following text blocks for factual inaccuracies and provide corrections according to the required JSON format.\n\n"
        "--- TEXT TO ANALYZE ---\n"
        f"{text_content}\n"
        "--- END OF TEXT ---"
    )
    return system_prompt, user_prompt


async def _call_llm_service(payload: dict) -> LLMQueryResponse:
    """Helper function to call the LLM Query microservice."""
    llm_service_url = urljoin(str(settings.LLM_QUERY_SERVICE_URL), "query")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(llm_service_url, json=payload, timeout=90.0)
            response.raise_for_status()
            return LLMQueryResponse(**response.json())
        except httpx.HTTPStatusError as e:
            downstream_error = e.response.text
            logger.error(f"LLM Query Service returned an error: {e.response.status_code} - {downstream_error}")
            return LLMQueryResponse(error_message=f"LLM Service Error: {downstream_error}")
        except httpx.RequestError as e:
            logger.error(f"Could not connect to LLM Query Service at {llm_service_url}: {e}")
            return LLMQueryResponse(error_message=f"Could not connect to dependent LLM Service: {e}")


async def generate_fact_check(request: FactCheckRequest) -> FactCheckResponse:
    """
    Generates fact-check suggestions by flattening note content and querying the LLM service.
    """
    flattened_text = _flatten_note_content(request.note_data)

    if not flattened_text.strip():
        return FactCheckResponse(check_type=request.check_type, corrections=[])

    system_prompt, user_prompt = _construct_llm_prompt(flattened_text)

    llm_payload = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt,
    }

    try:
        llm_response = await _call_llm_service(llm_payload)

        base_response_args = {
            "check_type": request.check_type,
            "model_used": llm_response.model_used
        }

        # --- START OF FIX ---
        # 1. Check for an explicit error message from the downstream service.
        if llm_response.error_message:
            return FactCheckResponse(**base_response_args, corrections=[], error_message=llm_response.error_message)

        # 2. **CRITICAL FIX:** Check if the response text is empty or None BEFORE parsing.
        if not llm_response.response_text:
            logger.warning("LLM service returned a successful status but with an empty response_text.")
            return FactCheckResponse(**base_response_args, corrections=[], error_message="LLM service returned an empty response, which may indicate an issue with the prompt or model.")
        # --- END OF FIX ---

        try:
            # Now it's safer to attempt parsing
            parsed_data = json.loads(llm_response.response_text.strip())
            validated_response = FactCheckResponse(**base_response_args, **parsed_data)
            return validated_response

        except (json.JSONDecodeError, Exception) as e:
            logger.exception(f"Failed to parse or validate LLM JSON for fact-check. LLM Response was: '{llm_response.response_text[:200]}...' Error: {e}")
            return FactCheckResponse(**base_response_args, corrections=[], error_message=f"Failed to process LLM response: {e}")

    except Exception as e:
        logger.exception(f"Unexpected error in fact-check generation service: {e}")
        return FactCheckResponse(
            check_type=request.check_type,
            corrections=[],
            error_message=f"An unexpected server error occurred: {e}"
        )