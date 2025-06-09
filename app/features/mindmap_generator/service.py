# app/features/mindmap_generator/service.py
import logging
from typing import Tuple, Optional
import os

from app.features.llm_query import llm_service
from app.features.mindmap_generator.schemas import MindmapRequest, MindmapResponse
from app.features.mindmap_generator.config import mindmap_generator_settings

logger = logging.getLogger(__name__)

# --- Cached Syntax Guide ---
_syntax_guide_content: Optional[str] = None


def _get_syntax_guide() -> str:
    """Reads the Mermaid mindmap syntax guide from the file and caches it."""
    global _syntax_guide_content
    if _syntax_guide_content is None:
        try:

            script_dir = os.path.dirname(os.path.abspath(__file__))
            guide_path = os.path.join(script_dir, "mindmap.md")

            with open(guide_path, 'r', encoding='utf-8') as f:
                _syntax_guide_content = f.read()
            logger.info(f"Successfully loaded and cached mindmap.md syntax guide from {guide_path}.")
        except FileNotFoundError:
            logger.error(
                f"FATAL: mindmap.md syntax guide not found at expected path: {guide_path}. Mindmap generation will fail.")
            _syntax_guide_content = "Error: Syntax guide file not found. Please ensure mindmap.md is in the app/features/mindmap_generator/ directory."
        except Exception as e:
            logger.exception(f"Error reading mindmap.md: {e}")
            _syntax_guide_content = f"Error reading syntax guide: {e}"

    return _syntax_guide_content


def _construct_llm_prompt(request: MindmapRequest) -> Tuple[str, str]:
    """Constructs the system and user prompts for the LLM."""

    # --- System Prompt ---
    system_prompt = (
        "You are an expert in creating Mermaid.js mind maps. Your task is to convert a given text into a valid Mermaid "
        "mind map syntax based on a comprehensive guide. Your output MUST be ONLY the Mermaid code, starting with "
        "`mindmap` on the first line. Do not include any other text, explanations, or markdown code fences like ```mermaid ... ```."
    )

    # --- User Prompt ---
    syntax_guide = _get_syntax_guide()
    root_node_name = request.root_node_name or "Root"

    user_prompt = f"""
### SYNTAX GUIDE START ###
{syntax_guide}
### SYNTAX GUIDE END ###

### TASK ###
Based on the strict syntax rules from the guide above, analyze the following text content and generate a hierarchical Mermaid mind map.
- The mind map must start with `mindmap` on the first line.
- Use indentation to define the hierarchy.
- The root node must be: {root_node_name}
- Structure the key ideas from the text as branches and sub-branches.

### TEXT CONTENT TO CONVERT ###
{request.text_content}
"""
    return system_prompt, user_prompt


def _clean_llm_response(response_text: str) -> str:
    """Cleans the raw LLM response to ensure it's valid Mermaid code."""
    cleaned_text = response_text.strip()

    # Remove markdown fences if the LLM ignores the prompt
    if cleaned_text.startswith("```mermaid"):
        cleaned_text = cleaned_text[len("```mermaid"):].strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:].strip()
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3].strip()

    # Ensure it starts with 'mindmap'
    if not cleaned_text.lower().startswith('mindmap'):
        # Be lenient, maybe it just forgot the first line
        cleaned_text = 'mindmap\n' + cleaned_text

    return cleaned_text


async def generate_mindmap(request: MindmapRequest) -> MindmapResponse:
    """
    Generates Mermaid mind map code by calling the LLM with a detailed, guided prompt.
    """
    system_prompt, user_prompt = _construct_llm_prompt(request)

    # Prepare LLM call parameters, allowing overrides from the request
    llm_params = request.extra_llm_params or {}
    max_tokens = llm_params.pop("max_tokens", mindmap_generator_settings.MINDMAP_MAX_TOKENS)
    temperature = llm_params.pop("temperature", mindmap_generator_settings.MINDMAP_TEMPERATURE)

    try:
        response_text, usage_info, error_message, model_used = await llm_service.generate_llm_response(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            additional_params=llm_params
        )

        if error_message:
            logger.error(f"LLM service returned an error for mind map generation: {error_message}")
            return MindmapResponse(error_message=f"LLM API Error: {error_message}")

        if not response_text:
            logger.error("LLM returned an empty response for mind map generation.")
            return MindmapResponse(error_message="LLM returned an empty response.")

        # Clean the response to get pure Mermaid code
        mermaid_code = _clean_llm_response(response_text)

        return MindmapResponse(
            mermaid_code=mermaid_code,
            model_used=model_used,
            usage_info=usage_info
        )

    except Exception as e:
        logger.exception(f"An unexpected error occurred in the mind map generation service: {e}")
        return MindmapResponse(error_message=f"An unexpected server error occurred: {str(e)}")