# app/services/llm_service.py
import logging
from openai import AsyncOpenAI # Using Async client
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    async_llm_client = AsyncOpenAI(
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL
    )
    logger.info("AsyncOpenAI client for Qwen-Plus initialized.")
except Exception as e:
    async_llm_client = None
    logger.exception("Failed to initialize AsyncOpenAI client for Qwen-Plus.")

async def generate_llm_response(
    system_prompt: str,
    user_prompt: str,
    model: str = settings.QWEN_DEFAULT_MODEL,
    max_tokens: int = 1500,
    temperature: float = 0.7
) -> str | None:
    if not async_llm_client:
        logger.error("LLM client not initialized. Cannot make API call.")
        return "Error: LLM client not available." # Or raise an exception

    logger.debug(f"Sending request to LLM. Model: {model}, System: '{system_prompt[:100]}...', User: '{user_prompt[:100]}...'")
    try:
        response = await async_llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            logger.debug(f"LLM response received (approx {len(content or '')} chars).")
            return content.strip() if content else None
        else:
            logger.warning("LLM response was empty or malformed.")
            return None
    except Exception as e:
        logger.exception(f"Error calling LLM API: {str(e)}")
        return f"Error interacting with LLM: {str(e)}" # Or raise