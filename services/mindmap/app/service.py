import logging
from typing import Tuple, Optional
import os
from urllib.parse import urljoin
import httpx

from .config import settings
from .schemas import MindmapRequest, MindmapResponse, LLMQueryResponse

logger = logging.getLogger(__name__)

_syntax_guide_content: Optional[str] = None

def _get_syntax_guide() -> str:
    """Reads the Mermaid mindmap syntax guide from the file and caches it."""
    global _syntax_guide_content
    if _syntax_guide_content is None:
        try:
            # Assumes mindmap.md is in the same directory as this service.py file
            guide_path = os.path.join(os.path.dirname(__file__), "mindmap.md")
            with open(guide_path, 'r', encoding='utf-8') as f:
                _syntax_guide_content = f.read()
            logger.info("Successfully loaded and cached mindmap.md syntax guide.")
        except Exception as e:
            _syntax_guide_content = "Error: Syntax guide file 'mindmap.md' not found."
            logger.error(f"{_syntax_guide_content} Details: {e}")
    return _syntax_guide_content

def _construct_llm_prompt(request: MindmapRequest) -> Tuple[str, str]:
    """Constructs the system and user prompts for the LLM."""
    system_prompt = (
        "You are an expert in creating Mermaid.js mind maps. Your task is to convert a given text into a valid Mermaid "
        "mind map syntax based on a comprehensive guide. Your output MUST be ONLY the Mermaid code, starting with "
        "`mindmap` on the first line. Do not include any other text, explanations, or markdown code fences like ```mermaid ... ```."
    )
    user_prompt = f"""
### SYNTAX GUIDE START ###
{_get_syntax_guide()}
### SYNTAX GUIDE END ###

### TASK ###
Based on the strict syntax rules from the guide, analyze the following text and generate a hierarchical Mermaid mind map.
- The mind map must start with `mindmap`.
- Use indentation for hierarchy.
- The root node must be: {request.root_node_name}
- Structure key ideas from the text as branches.

### TEXT CONTENT TO CONVERT ###
{request.text_content}
"""
    return system_prompt, user_prompt

def _clean_llm_response(response_text: str) -> str:
    """Cleans the raw LLM response to ensure it's valid Mermaid code."""
    cleaned_text = response_text.strip()
    if cleaned_text.startswith("```mermaid"):
        cleaned_text = cleaned_text[len("```mermaid"):].strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:].strip()
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3].strip()
    if not cleaned_text.lower().startswith('mindmap'):
        cleaned_text = 'mindmap\n' + cleaned_text
    return cleaned_text

async def _call_llm_service(payload: dict) -> LLMQueryResponse:
    """Helper function to call the LLM Query microservice."""
    llm_service_url = urljoin(str(settings.LLM_QUERY_SERVICE_URL), "query")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(llm_service_url, json=payload, timeout=90.0)
            response.raise_for_status()
            return LLMQueryResponse(**response.json())
        except httpx.HTTPStatusError as e:
            return LLMQueryResponse(error_message=f"LLM Service Error: {e.response.text}")
        except httpx.RequestError as e:
            return LLMQueryResponse(error_message=f"Could not connect to LLM Service: {e}")

async def generate_mindmap(request: MindmapRequest) -> MindmapResponse:
    """Generates Mermaid code by calling the LLM service."""
    system_prompt, user_prompt = _construct_llm_prompt(request)

    llm_params = request.extra_llm_params or {}
    llm_payload = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt,
        "max_tokens": llm_params.pop("max_tokens", settings.MINDMAP_MAX_TOKENS),
        "temperature": llm_params.pop("temperature", settings.MINDMAP_TEMPERATURE),
        "additional_params": llm_params
    }

    try:
        llm_response = await _call_llm_service(llm_payload)
        if llm_response.error_message:
            return MindmapResponse(error_message=llm_response.error_message)
        if not llm_response.response_text:
            return MindmapResponse(error_message="LLM service returned an empty response.")

        mermaid_code = _clean_llm_response(llm_response.response_text)
        return MindmapResponse(
            mermaid_code=mermaid_code,
            model_used=llm_response.model_used,
            usage_info=llm_response.usage_info
        )
    except Exception as e:
        logger.exception(f"Unexpected error in mindmap generation service: {e}")
        return MindmapResponse(error_message=f"An unexpected server error occurred: {e}")