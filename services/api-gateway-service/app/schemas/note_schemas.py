# app/schemas/note_schemas.py
import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

# Schema for the request body when CREATING a note
class NoteCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    text: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None

# Schema for the request body when UPDATING a note
class NoteUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    text: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None

# Schema for the response body when returning a note
class NoteResponse(BaseModel):
    id: int
    owner_id: int
    title: str
    text: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None
    creation_date: Optional[datetime.datetime] = None
    version: int

    class Config:
        from_attributes = True

# Schema for the request body when asking for a summary
class NoteSummaryRequest(BaseModel):
    summary_level: Literal["short", "medium", "detailed"] = Field(
        "medium",
        description="The desired length and detail of the summary."
    )

# Schema for the response body when returning a summary
class NoteSummaryResponse(BaseModel):
    summary_text: str
    model_used: Optional[str] = None
    level_used: Literal["short", "medium", "detailed"]
    strategy_used: Literal["root_only"]

class Correction(BaseModel):
    """A single identified inaccuracy and its suggested correction."""
    note_id: int = Field(..., description="The ID of the note containing the inaccuracy.")
    inaccurate_quote: str
    issue: str
    suggested_correction: str

class FactCheckResponse(BaseModel):
    """The response model for a fact-check request from the gateway's perspective."""
    model_used: Optional[str] = None
    check_type: Literal["corrective_suggestions"]
    corrections: List[Correction]


class CorrectionToApply(BaseModel):
    """
    Defines a single correction to be applied. This is sent by the client
    in a 'guided' update request. It mirrors the 'Correction' schema.
    """
    note_id: int
    inaccurate_quote: str
    suggested_correction: str

class GuidedUpdateRequest(BaseModel):
    """The request body for a guided update operation."""
    corrections_to_apply: List[CorrectionToApply] = Field(..., description="The list of specific fixes to apply.")

class ChangeDetail(BaseModel):
    """Describes a single change made by the update service."""
    note_id: int
    change_classification: Literal["incorrect", "outdated"]
    original_info: str
    updated_info: str
    reason: str

class UpdateResponse(BaseModel):
    """The unified response from either an autonomous or guided update."""
    strategy_used: Literal["autonomous", "guided"]
    model_used: Optional[str] = None
    updated_text: str
    changes: List[ChangeDetail]
