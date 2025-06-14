import logging
import json
from typing import Tuple, Optional
import httpx
from urllib.parse import urljoin

from .config import settings
from .schemas import QuizRequest, QuizResponse, LLMQueryResponse

logger = logging.getLogger(__name__)

def _construct_llm_prompt(request: QuizRequest) -> Tuple[str, str]:
    """Constructs the system and user prompts for the LLM based on the quiz request."""
    system_prompt = json.dumps([
        "You are an expert educational content creator. Your task is to generate a quiz.",
        "You MUST reply ONLY with a single, valid JSON object that strictly adheres to the provided schema. Do not include any text, pleasantries, or markdown formatting before or after the JSON object.",
        "The JSON schema for your response is as follows:",
        QuizResponse.model_json_schema()
    ], indent=2)

    user_prompt_parts = {
        "instruction": "Generate the quiz now based on the following specifications.",
        "specifications": {
            "title_suggestion": f"A quiz about the provided context with {request.difficulty} difficulty.",
            "number_of_questions": request.questions,
            "difficulty_level": request.difficulty,
            "knowledge_source_mode": request.mode
        }
    }
    if request.mode in ["user_context", "hybrid"]:
        user_prompt_parts["context_to_use"] = request.context

    return system_prompt, json.dumps(user_prompt_parts, indent=2)

async def _call_llm_service(payload: dict) -> LLMQueryResponse:
    """Helper function to call the LLM Query microservice."""
    llm_service_url = urljoin(str(settings.LLM_QUERY_SERVICE_URL), "query")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(llm_service_url, json=payload, timeout=60.0)
            response.raise_for_status()
            return LLMQueryResponse(**response.json())
        except httpx.HTTPStatusError as e:
            # The error response from the downstream service is often in e.response.text
            downstream_error = e.response.text
            logger.error(f"LLM Query Service returned an error: {e.response.status_code} - {downstream_error}")
            return LLMQueryResponse(error_message=f"LLM Service Error: {downstream_error}")
        except httpx.RequestError as e:
            logger.error(f"Could not connect to LLM Query Service at {llm_service_url}: {e}")
            return LLMQueryResponse(error_message=f"Could not connect to dependent LLM Service: {e}")

async def generate_quiz(request: QuizRequest) -> QuizResponse:
    """Generates a quiz by calling the LLM service and parsing the response."""
    if request.mode in ["user_context", "hybrid"] and not request.context:
        return QuizResponse(context_mode=request.mode, error_message="Error: 'context' field is required for this mode.")

    system_prompt, user_prompt = _construct_llm_prompt(request)

    llm_params = request.extra_llm_params or {}
    llm_payload = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt,
        "max_tokens": llm_params.pop("max_tokens", settings.QUIZ_MAX_TOKENS),
        "temperature": llm_params.pop("temperature", settings.QUIZ_DEFAULT_TEMPERATURE),
        "additional_params": llm_params
    }

    try:
        llm_response = await _call_llm_service(llm_payload)

        if llm_response.error_message:
            return QuizResponse(context_mode=request.mode, error_message=llm_response.error_message)
        if not llm_response.response_text:
            return QuizResponse(context_mode=request.mode, error_message="LLM service returned an empty response.")

        try:
            response_text = llm_response.response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-4].strip()

            quiz_data = json.loads(response_text)
            quiz_response = QuizResponse.model_validate(quiz_data)
            quiz_response.model_used = llm_response.model_used
            return quiz_response

        except (json.JSONDecodeError, Exception) as e:
            logger.exception(f"Failed to parse or validate LLM JSON for quiz. Error: {e}")
            return QuizResponse(context_mode=request.mode, error_message=f"Failed to process LLM response: {e}")

    except Exception as e:
        logger.exception(f"Unexpected error in quiz generation service: {e}")
        return QuizResponse(context_mode=request.mode, error_message=f"An unexpected server error occurred: {e}")