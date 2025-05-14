# app/schemas/document.py

from pydantic import BaseModel, Field
from typing import Optional
from pydantic import HttpUrl

# --- Document Type Schemas ---
class DocumentTypeBase(BaseModel):
    name: str = Field(..., max_length=255)

class DocumentTypeCreate(DocumentTypeBase):
    pass # No extra fields needed for creation usually

class DocumentTypeResponse(DocumentTypeBase):
    id: int
    version: int

    class Config:
        from_attributes = True

# --- Document Schemas ---
class DocumentBase(BaseModel):
    doc_type_id: int
    comment: Optional[str] = Field(None, max_length=255)
    mime_type: Optional[str] = Field(None, max_length=255)
    owned_by_id: Optional[int] = None
    url: Optional[str] = Field(None, max_length=255) # Validate as URL if needed: HttpUrl
    path: str = Field(..., max_length=255)
    name: str = Field(..., max_length=255)

class DocumentCreate(DocumentBase):
    # Often you don't provide owned_by_id directly, it comes from logged-in user context
    owned_by_id: Optional[int] = None # Make optional here, set in service layer

class DocumentResponse(DocumentBase):
    id: int
    # Maybe include related data if needed?
    # doc_type: DocumentTypeResponse
    # owned_by: Optional[AppUserResponse] # Avoid circular imports carefully

    class Config:
        from_attributes = True


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)

class DocumentUpdate(BaseModel):
    doc_type_id: Optional[int] = None
    comment: Optional[str] = Field(None, max_length=255)
    mime_type: Optional[str] = Field(None, max_length=255)
    owned_by_id: Optional[int] = None # Allow changing owner
    url: Optional[str] = Field(None, max_length=255)
    path: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    # Add other updatable fields

class DocumentTypeUpdate(BaseModel):
    """
    Schema for updating an existing DocumentType.
    Allows updating the name.
    """
    name: Optional[str] = Field(None, max_length=255, description="The new name for the document type.")
    # Add other fields here if they should be updatable, marked as Optional

    model_config = { # Pydantic v2 config example
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Updated Web Page Type"
                }
            ]
        }
    }

class DocumentCreateFromUrlRequest(BaseModel):
    url: HttpUrl # Use HttpUrl for validation
    name: str = Field(..., max_length=255, description="User-defined name for this URL reference")
    doc_type_id: int
    comment: Optional[str] = Field(None, max_length=255)
    link_to_note_id: Optional[int] = Field(None, description="Optional ID of a Note to link this document to upon creation.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://example.com/article.html",
                    "name": "Example Article Online",
                    "doc_type_id": 1, # Assuming a DocumentType with ID 1 exists
                    "comment": "Reference to an online article.",
                    "link_to_note_id": 101 # Assuming a Note with ID 101 exists
                }
            ]
        }
    }