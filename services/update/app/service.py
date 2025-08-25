# services/update/app/service.py (Fully Refactored and Corrected)

import logging
import json
from typing import List, Tuple, Optional
import httpx
from urllib.parse import urljoin
from .config import settings
from .schemas import (
    UpdateRequest, UpdateResponse, LLMQueryResponse, NoteData, ChangeDetail, CorrectionToApply
)

logger = logging.getLogger(__name__)


# --- Helper Functions ---

def _flatten_note_content(note: NoteData) -> str:
    """Recursively flattens a note and its sub-notes into a single string."""
    content_parts = []
    note_block = (f"--- NOTE START (ID: {note.note_id}) ---\n"
                  f"Title: {note.title}\n"
                  f"Content: {note.text_content or ''}\n"
                  f"--- NOTE END (ID: {note.note_id}) ---")
    content_parts.append(note_block)
    if note.sub_notes:
        for sub_note in note.sub_notes:
            content_parts.append(_flatten_note_content(sub_note))
    return "\n\n".join(content_parts)


def _get_clean_text_from_note(note_data: NoteData) -> str:
    """Creates a clean, marker-free text block from note data."""
    notes = [note_data] + (note_data.sub_notes or [])
    return "\n\n".join(
        [f"{note.title}\n{note.text_content or ''}".strip() for note in notes]
    ).strip()


async def _call_llm_service(payload: dict) -> LLMQueryResponse:
    """Helper function to call the LLM Query microservice."""
    llm_service_url = urljoin(str(settings.LLM_QUERY_SERVICE_URL), "query")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(llm_service_url, json=payload, timeout=120.0)
            response.raise_for_status()
            return LLMQueryResponse(**response.json())
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"LLM Service Error: {e.response.status_code} - {error_text}")
            return LLMQueryResponse(error_message=f"LLM Service Error: {error_text}")
        except httpx.RequestError as e:
            logger.error(f"LLM Connection Error: {e}")
            return LLMQueryResponse(error_message=f"LLM Connection Error: {e}")


# --- Prompt Engineering ("Analyst -> Copyeditor" Pattern) ---

def _get_analysis_prompt(text_content: str) -> tuple[str, str]:
    """Prompt for Step 1 (The "Analyst"): Hardened with a high-quality example."""
    json_schema = {"changes": [
        {"note_id": 101, "change_classification": "outdated", "original_info": "...", "updated_info": "...",
         "reason": "..."}]}

    good_example = {"changes": [
        {"note_id": 101, "change_classification": "outdated",
         "original_info": "In 2016, the flagship smartphone was the iPhone 7.",
         "updated_info": "In recent years, a flagship smartphone is the iPhone 15.",
         "reason": "The iPhone 7 was released in 2016; technology has advanced significantly, with newer models like the iPhone 15 now being current."},
        {"note_id": 101, "change_classification": "incorrect", "original_info": "The capital of Australia is Sydney.",
         "updated_info": "The capital of Australia is Canberra.",
         "reason": "While Sydney is Australia's largest city, Canberra has been the nation's capital since 1927."},
        {"note_id": 102, "change_classification": "outdated",
         "original_info": "The most popular app for short-form video content was Vine.",
         "updated_info": "The most popular app for short-form video content is now TikTok.",
         "reason": "Vine was a popular short-form video app until it was shut down in 2017; TikTok is now the dominant platform in this category."}
    ]}

    system_prompt = (
        "You are a hyper-vigilant fact-checking analyst. Your task is to analyze text and generate a structured JSON report of all outdated or incorrect facts.\n\n"
        "You MUST follow these rules without exception:\n"
        "1. **ONE OBJECT PER ERROR:** You MUST create a separate JSON object for EACH distinct factual error you find, even if multiple errors are in the same note.\n"
        "2. **CLASSIFY CORRECTLY:** You MUST use the `change_classification` field. Use 'outdated' for information that was once true but is now superseded. Use 'incorrect' for information that was never factually true.\n"
        "3. **WRITE RICH REASONS:** The `reason` field MUST be a detailed, explanatory sentence that provides valuable context. Do NOT use lazy reasons like 'Information was outdated'.\n"
        "4. **STRICT JSON OUTPUT:** Your entire response MUST be a single, valid JSON object. If no changes are needed, you MUST return `{\"changes\": []}`.\n\n"
        "--- PERFECT OUTPUT EXAMPLE ---\n"
        f"{json.dumps(good_example, indent=2)}\n\n"
        f"--- REQUIRED JSON SCHEMA ---\n{json.dumps(json_schema, indent=2)}"
    )
    user_prompt = f"Please analyze the following text and generate the JSON report of changes, following all rules and matching the example's quality:\n\n{text_content}"
    return system_prompt, user_prompt


def _get_rewrite_prompt(note_data: NoteData, changes: List[ChangeDetail]) -> tuple[str, str]:
    """Prompt for Step 2 (The "Copyeditor"): Perform a high-quality rewrite."""
    system_prompt = (
        "You are an expert copyeditor. Your task is to revise the 'ORIGINAL TEXT' by flawlessly applying the 'LIST OF CHANGES'.\n\n"
        "You MUST adhere to these rules:\n"
        "1. **Apply All Changes:** Intelligently integrate all 'updated_info' from the list into the text.\n"
        "2. **Ensure Narrative Flow:** The final text must be a single, coherent narrative.\n"
        "3. **CLEAN OUTPUT IS ESSENTIAL:** Your response MUST NOT contain any structural markers like 'Title:' or 'Content:'.\n"
        "4. **TEXT ONLY:** Respond ONLY with the full, final, updated text as a single string."
    )
    clean_original_text = _get_clean_text_from_note(note_data)
    change_list_str = json.dumps([c.dict() for c in changes], indent=2)
    user_prompt = (f"--- ORIGINAL TEXT ---\n{clean_original_text}\n\n"
                   f"--- LIST OF CHANGES TO APPLY ---\n{change_list_str}\n\n"
                   "Please provide only the fully rewritten text now.")
    return system_prompt, user_prompt


# --- Refactored Service Logic ---

async def _run_autonomous_analysis(flattened_text: str) -> Tuple[List[ChangeDetail], Optional[str], Optional[str]]:
    """Runs Step 1: Analyzes text and returns a list of changes, model used, and any error."""
    system_prompt, user_prompt = _get_analysis_prompt(flattened_text)
    llm_response = await _call_llm_service({"system_prompt": system_prompt, "user_prompt": user_prompt})

    if llm_response.error_message or not llm_response.response_text:
        error = llm_response.error_message or "Analysis step failed to produce a response."
        return [], llm_response.model_used, error

    try:
        analysis_data = json.loads(llm_response.response_text)
        list_of_changes = [ChangeDetail(**change) for change in analysis_data.get("changes", [])]
        return list_of_changes, llm_response.model_used, None
    except Exception as e:
        logger.exception(f"Failed to parse analysis from LLM. Response: {llm_response.response_text}")
        return [], llm_response.model_used, f"Analysis step failed to return valid JSON: {e}"


async def _run_rewrite_step(note_data: NoteData, changes: List[ChangeDetail],
                            initial_model: Optional[str]) -> UpdateResponse:
    """Runs Step 2: Rewrites text based on the list of changes."""
    system_prompt, user_prompt = _get_rewrite_prompt(note_data, changes)
    llm_response = await _call_llm_service({"system_prompt": system_prompt, "user_prompt": user_prompt})

    final_model = llm_response.model_used or initial_model
    if llm_response.error_message or not llm_response.response_text:
        return UpdateResponse(
            strategy_used="autonomous", model_used=final_model, updated_text="",
            changes=changes, error_message=llm_response.error_message or "Rewrite step failed."
        )

    return UpdateResponse(
        strategy_used="autonomous", model_used=final_model,
        updated_text=llm_response.response_text.strip(), changes=changes
    )


async def generate_update(request: UpdateRequest) -> UpdateResponse:
    """Orchestrates the update process based on the chosen strategy."""
    list_of_changes: List[ChangeDetail] = []
    model_used: Optional[str] = None
    error: Optional[str] = None

    if request.strategy == "autonomous":
        flattened_text = _flatten_note_content(request.note_data)
        list_of_changes, model_used, error = await _run_autonomous_analysis(flattened_text)
        if error:
            return UpdateResponse(strategy_used="autonomous", updated_text="", changes=[], error_message=error)

    elif request.strategy == "guided" and request.corrections_to_apply:
        for correction in request.corrections_to_apply:
            list_of_changes.append(ChangeDetail(
                note_id=correction.note_id,
                change_classification="incorrect",
                original_info=correction.inaccurate_quote,
                updated_info=correction.suggested_correction,
                reason="Applying user-provided correction."
            ))

    # If no changes were found or provided, return the cleaned original text.
    if not list_of_changes:
        clean_text = _get_clean_text_from_note(request.note_data)
        return UpdateResponse(
            strategy_used=request.strategy, model_used=model_used,
            updated_text=clean_text, changes=[]
        )

    # Proceed to the rewrite step for either strategy if changes exist.
    return await _run_rewrite_step(request.note_data, list_of_changes, model_used)