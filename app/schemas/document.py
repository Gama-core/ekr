# app/schemas/document.py

from pydantic import BaseModel, Field
from typing import Optional

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