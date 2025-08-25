from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- Schemas for this service's API contract ---

class NoteData(BaseModel):
    """
    Recursive model for nested notes.
    For the 'root_only' strategy, the service will ONLY use the top-level
    title and text_content. The sub_notes field is included for future compatibility.
    """
    title: str
    text_content: Optional[str] = None
    sub_notes: Optional[List['NoteData']] = []

# This allows the recursive 'NoteData' definition to work
NoteData.model_rebuild()


class SummaryRequest(BaseModel):
    """The request model for the summary service."""
    note_data: NoteData = Field(..., description="The note object to be summarized.")

    summary_level: Literal["short", "medium", "detailed"] = Field(
        "medium", description="Controls the desired length and detail of the summary."
    )

    summary_strategy: Literal["root_only"] = Field(
        "root_only",
        description="The summarization strategy. Currently, only 'root_only' is supported."
    )


class SummaryResponse(BaseModel):
    """The response model for a successful summary generation."""
    summary_text: Optional[str] = None
    model_used: Optional[str] = None
    level_used: Literal["short", "medium", "detailed"]
    strategy_used: Literal["root_only"]
    error_message: Optional[str] = None


# --- Schemas for communicating with the LLM Query Service ---

class LLMUsageInfo(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class LLMQueryResponse(BaseModel):
    response_text: Optional[str] = None
    model_used: Optional[str] = None
    usage_info: Optional[LLMUsageInfo] = None
    error_message: Optional[str] = None