# app/schemas/link.py

from pydantic import BaseModel, Field
from typing import Optional

class LinkBase(BaseModel):
    link_type: Optional[str] = Field(None, max_length=255)
    destination_id: Optional[int] = None # Link to internal Note ID
    source_id: Optional[int] = None      # Link from internal Note ID
    url: Optional[str] = Field(None, max_length=255) # External URL
    is_web_link: Optional[bool] = False


class LinkCreate(LinkBase):
    # version is usually handled by DB/ORM
     version: Optional[int] = 0


class LinkResponse(LinkBase):
    id: int
    version: int

    class Config:
        from_attributes = True

class LinkUpdate(BaseModel):
    link_type: Optional[str] = Field(None, max_length=255)
    destination_id: Optional[int] = None
    source_id: Optional[int] = None
    url: Optional[str] = Field(None, max_length=255)
    is_web_link: Optional[bool] = None