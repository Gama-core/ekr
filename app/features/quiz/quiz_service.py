# app/features/quiz/quiz_service.py
import logging
import json
from typing import Tuple, Optional
import uuid

from app.features.llm_query import llm_service
from app.features.quiz.schemas import QuizRequest, QuizResponse, QuizQuestion, QuizOption
from app.features.quiz.config import quiz_settings

logger = logging.getLogger(__name__)

def _construct_llm_prompt(request: QuizRequest) -> Tuple[str, str]:
    """Constructs the system and user prompts for the LLM based on the quiz request."""

    # --- System Prompt ---
    system_prompt_parts = [
        "You are an expert educational content creator. Your task is to generate a quiz.",
        "You MUST reply ONLY with a single, valid JSON object that strictly adheres to the provided schema. Do not include any text, pleasantries, or markdown formatting before or after the JSON object.",
        "The JSON schema for your response is as follows:",
        # Dynamically generate the JSON schema from Pydantic models to ensure it's always up-to-date
        QuizResponse.model_json_schema()
    ]
    system_prompt = json.dumps(system_prompt_parts, indent=2)


    # --- User Prompt ---
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

    user_prompt = json.dumps(user_prompt_parts, indent=2)

    return system_prompt, user_prompt


async def generate_quiz(request: QuizRequest) -> QuizResponse:
    """
    Generates a quiz by calling the LLM, parsing the response, and formatting it.
    """
    if request.mode in ["user_context", "hybrid"] and not request.context:
        return QuizResponse(
            context_mode=request.mode,
            error_message="Error: 'context' field is required when mode is 'user_context' or 'hybrid'."
        )

    system_prompt, user_prompt = _construct_llm_prompt(request)

    # Prepare LLM call parameters
    llm_params = request.extra_llm_params or {}
    max_tokens = llm_params.pop("max_tokens", quiz_settings.QUIZ_MAX_TOKENS)
    temperature = llm_params.pop("temperature", quiz_settings.QUIZ_DEFAULT_TEMPERATURE)

    try:
        response_text, _, error_message, model_used = await llm_service.generate_llm_response(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            additional_params=llm_params
        )

        if error_message:
            logger.error(f"LLM service returned an error for quiz generation: {error_message}")
            return QuizResponse(context_mode=request.mode, error_message=f"LLM API Error: {error_message}")

        if not response_text:
            logger.error("LLM returned an empty response for quiz generation.")
            return QuizResponse(context_mode=request.mode, error_message="LLM returned an empty response.")

        # Parse the JSON response from the LLM
        try:
            # Clean up potential markdown code fences
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-4]

            quiz_data = json.loads(response_text)
            # Validate the parsed data against our Pydantic model
            quiz_response = QuizResponse.model_validate(quiz_data)
            quiz_response.model_used = model_used # Add the model name to the final response
            return quiz_response

        except json.JSONDecodeError as e:
            logger.exception(f"Failed to decode JSON from LLM response. Error: {e}\nResponse text: '{response_text[:500]}...'")
            return QuizResponse(context_mode=request.mode, error_message=f"Failed to parse LLM response as JSON. Detail: {e}")
        except Exception as pydantic_error: # Catches Pydantic validation errors
            logger.exception(f"Pydantic validation failed for LLM response. Error: {pydantic_error}")
            return QuizResponse(context_mode=request.mode, error_message=f"LLM response did not match the required quiz structure. Detail: {pydantic_error}")


    except Exception as e:
        logger.exception(f"An unexpected error occurred in the quiz generation service: {e}")
        return QuizResponse(context_mode=request.mode, error_message=f"An unexpected server error occurred: {str(e)}")