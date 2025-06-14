import logging
from openai import AsyncOpenAI, OpenAIError
from typing import Optional, Tuple, Dict, Any

from .config import settings
from .schemas import LLMUsageInfo, LLMQueryRequest

logger = logging.getLogger(__name__)

# This client is initialized once when the module is loaded.
async_llm_client: Optional[AsyncOpenAI] = None

def initialize_llm_client():
    """Initializes the global async_llm_client."""
    global async_llm_client
    if settings.QWEN_API_KEY:
        try:
            async_llm_client = AsyncOpenAI(
                api_key=settings.QWEN_API_KEY.get_secret_value(),
                base_url=settings.QWEN_BASE_URL
            )
            logger.info("AsyncOpenAI client for LLM queries initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize AsyncOpenAI client.")
            async_llm_client = None
    else:
        logger.error("LLM client not initialized because QWEN_API_KEY is missing.")

async def generate_llm_response(
    request: LLMQueryRequest
) -> Tuple[Optional[str], Optional[LLMUsageInfo], Optional[str], Optional[str]]:
    """
    Generates a response from the LLM based on the request model.
    Returns: A tuple (response_text, usage_info, error_message, actual_model_used)
    """
    if not async_llm_client:
        error_msg = "LLM client not available. Check service configuration and logs."
        logger.error(error_msg)
        return None, None, error_msg, None

    actual_model = request.model_name or settings.QWEN_DEFAULT_MODEL
    actual_max_tokens = request.max_tokens or settings.DEFAULT_MAX_TOKENS
    actual_temperature = request.temperature if request.temperature is not None else settings.DEFAULT_TEMPERATURE

    messages = [{"role": "user", "content": request.user_prompt}]
    if request.system_prompt:
        messages.insert(0, {"role": "system", "content": request.system_prompt})

    request_params = {
        "model": actual_model,
        "messages": messages,
        "max_tokens": actual_max_tokens,
        "temperature": actual_temperature,
    }
    if request.additional_params:
        request_params.update(request.additional_params)

    logger.debug(f"Sending request to LLM: model={actual_model}, max_tokens={actual_max_tokens}")

    try:
        api_response = await async_llm_client.chat.completions.create(**request_params)

        response_text = api_response.choices[0].message.content if api_response.choices else None

        usage_data: Optional[LLMUsageInfo] = None
        if api_response.usage:
            usage_data = LLMUsageInfo(
                prompt_tokens=api_response.usage.prompt_tokens,
                completion_tokens=api_response.usage.completion_tokens,
                total_tokens=api_response.usage.total_tokens
            )

        if not response_text:
             logger.warning(f"LLM response for model {actual_model} was empty.")
             return None, usage_data, "LLM returned an empty response.", actual_model

        return response_text.strip(), usage_data, None, actual_model

    except OpenAIError as e:
        error_msg = f"OpenAI API Error: {type(e).__name__} - {e}"
        logger.error(error_msg, exc_info=True)
        return None, None, error_msg, actual_model
    except Exception as e:
        error_msg = f"Unexpected error calling LLM API: {type(e).__name__} - {e}"
        logger.exception(error_msg)
        return None, None, error_msg, actual_model