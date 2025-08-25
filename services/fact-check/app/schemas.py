import json
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- Schemas for this service's API contract ---

class NoteData(BaseModel):
    """Recursive model for nested notes, now requiring a note_id."""
    note_id: int = Field(..., description="The unique identifier for this note.")
    title: str
    text_content: Optional[str] = None
    sub_notes: Optional[List['NoteData']] = []

NoteData.model_rebuild()

class FactCheckRequest(BaseModel):
    """The request model for the fact-check service."""
    note_data: NoteData = Field(..., description="The note object to be fact-checked.")
    check_type: Literal["corrective_suggestions"] = Field(
        "corrective_suggestions",
        description="The type of fact-check to perform."
    )

class Correction(BaseModel):
    """A single identified inaccuracy and its suggested correction, now with note_id."""
    note_id: int = Field(..., description="The ID of the note containing the inaccuracy.")
    inaccurate_quote: str = Field(..., description="The exact text of the inaccurate statement.")
    issue: str = Field(..., description="A brief, one-sentence description of the error.")
    suggested_correction: str = Field(..., description="A revised version of the statement that is factually accurate.")

class FactCheckResponse(BaseModel):
    """The response model for a successful fact-check."""
    model_used: Optional[str] = None
    check_type: Literal["corrective_suggestions"]
    corrections: List[Correction] = Field(..., description="A list of identified inaccuracies and their corrections.")
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