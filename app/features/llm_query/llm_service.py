# app/features/llm_query/llm_service.py
import logging
from openai import AsyncOpenAI, OpenAIError # Using Async client
from typing import Optional, Tuple, Dict, Any

# Import global core settings for API keys and base URLs
from app.core.config import settings as core_settings
# Import feature-specific settings and schemas
from app.features.llm_query.config import llm_query_settings
from app.features.llm_query.schemas import LLMUsageInfo

logger = logging.getLogger(__name__)

# Initialize the AsyncOpenAI client (for Qwen or other OpenAI-compatible APIs)
# This client is initialized once when the module is loaded.
try:
    async_llm_client = AsyncOpenAI(
        api_key=core_settings.QWEN_API_KEY,
        base_url=core_settings.QWEN_BASE_URL
    )
    logger.info(f"AsyncOpenAI client for LLM queries initialized (Base URL: {core_settings.QWEN_BASE_URL}).")
except Exception as e:
    async_llm_client = None # type: ignore
    logger.exception("Failed to initialize AsyncOpenAI client for LLM queries.")

async def generate_llm_response(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    additional_params: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Optional[LLMUsageInfo], Optional[str], Optional[str]]:
    """
    Generates a response from the LLM.

    Returns:
        A tuple: (response_text, usage_info, error_message, actual_model_used)
    """
    if not async_llm_client:
        error_msg = "LLM client not initialized. Cannot make API call."
        logger.error(error_msg)
        return None, None, error_msg, None

    actual_model = model_name or core_settings.QWEN_DEFAULT_MODEL
    actual_max_tokens = max_tokens or llm_query_settings.DEFAULT_MAX_TOKENS
    actual_temperature = temperature if temperature is not None else llm_query_settings.DEFAULT_TEMPERATURE

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    request_params = {
        "model": actual_model,
        "messages": messages,
        "max_tokens": actual_max_tokens,
        "temperature": actual_temperature,
    }
    if additional_params:
        request_params.update(additional_params) # Merge any extra params

    logger.debug(
        f"Sending request to LLM. Model: {actual_model}, "
        f"System: '{system_prompt[:100] if system_prompt else 'None'}...', "
        f"User: '{user_prompt[:100]}...', "
        f"MaxTokens: {actual_max_tokens}, Temp: {actual_temperature}"
    )

    try:
        response = await async_llm_client.chat.completions.create(**request_params) # type: ignore

        response_text: Optional[str] = None
        usage_data: Optional[LLMUsageInfo] = None

        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            response_text = content.strip() if content else None
            logger.debug(f"LLM response received (approx {len(response_text or '')} chars).")

        if response.usage:
            usage_data = LLMUsageInfo(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
            logger.debug(f"LLM Usage: {usage_data.model_dump_json()}")

        if not response_text and not usage_data: # Check if response was effectively empty
             logger.warning(f"LLM response for model {actual_model} was empty or malformed.")
             return None, usage_data, "LLM response was empty or malformed.", actual_model


        return response_text, usage_data, None, actual_model

    except OpenAIError as e: # Catch specific OpenAI client errors
        error_msg = f"OpenAI API Error ({type(e).__name__}) for model {actual_model}: {str(e)}"
        logger.error(error_msg, exc_info=True) # Log with traceback for OpenAI errors
        return None, None, error_msg, actual_model
    except Exception as e:
        error_msg = f"Unexpected error calling LLM API for model {actual_model}: {type(e).__name__} - {str(e)}"
        logger.exception(error_msg) # Log with traceback for unexpected errors
        return None, None, error_msg, actual_model