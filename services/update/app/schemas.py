import json
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal

# --- Common Schemas ---

class NoteData(BaseModel):
    """Recursive model for nested notes, requiring a note_id."""
    note_id: int = Field(..., description="The unique identifier for this note.")
    title: str
    text_content: Optional[str] = None
    sub_notes: Optional[List['NoteData']] = []

NoteData.model_rebuild()

class CorrectionToApply(BaseModel):
    """A single correction to be applied in 'guided' mode."""
    note_id: int
    inaccurate_quote: str
    suggested_correction: str

class ChangeDetail(BaseModel):
    """Describes a single change made to the text."""
    note_id: int = Field(..., description="The ID of the note where the change was made.")
    # --- NAME CHANGE IMPLEMENTED HERE ---
    change_classification: Literal["incorrect", "outdated"] = Field(..., description="The classification of the change.")
    original_info: str = Field(..., description="The specific outdated or incorrect text that was replaced.")
    updated_info: str = Field(..., description="The new text that replaced the original info.")
    reason: str = Field(..., description="A detailed explanation for why the change was necessary, providing context.")

# --- Unified Response and Request Schemas ---

class UpdateResponse(BaseModel):
    """Unified response model for both strategies."""
    strategy_used: Literal["autonomous", "guided"]
    model_used: Optional[str] = None
    updated_text: str = Field(..., description="The complete, revised version of the document, clean of any markers.")
    changes: List[ChangeDetail] = Field(..., description="A detailed log of all modifications made.")
    error_message: Optional[str] = None

class UpdateRequest(BaseModel):
    """Unified request model for both strategies."""
    strategy: Literal["autonomous", "guided"]
    note_data: NoteData
    corrections_to_apply: Optional[List[CorrectionToApply]] = None

    @model_validator(mode='before')
    def check_guided_requirements(cls, data):
        strategy = data.get('strategy')
        corrections = data.get('corrections_to_apply')
        if strategy == 'guided' and not corrections:
            raise ValueError("'corrections_to_apply' must be provided for the 'guided' strategy.")
        if strategy == 'autonomous' and corrections:
            raise ValueError("'corrections_to_apply' should not be provided for the 'autonomous' strategy.")
        return data

# --- Schemas for communicating with the LLM Query Service ---

class LLMQueryResponse(BaseModel):
    response_text: Optional[str] = None
    model_used: Optional[str] = None
    error_message: Optional[str] = None