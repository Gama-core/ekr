# app/schemas/link.py

from pydantic import BaseModel, Field, HttpUrl # Added HttpUrl for optional URL validation
from typing import Optional

class LinkBase(BaseModel):
    link_type: Optional[str] = Field(None, max_length=255, description="Type of the link (e.g., 'related_to', 'cites', 'source_url').")
    destination_id: Optional[int] = Field(None, description="ID of the destination Note for an internal link.")
    source_id: Optional[int] = Field(None, description="ID of the source Note for an internal link.")
    url: Optional[HttpUrl] = Field(None, description="External URL for a web link. Use HttpUrl for validation.") # Changed to HttpUrl
    is_web_link: Optional[bool] = Field(False, description="True if this is an external web link, False for internal note-to-note link.")


class LinkCreate(LinkBase):
    # Version is usually handled by DB/ORM, not client input for create
    # version: Optional[int] = 0 # This was in your schema, typically not needed in Create

    model_config = { # Pydantic v2 example
        "json_schema_extra": {
            "examples": [
                { # Internal link
                    "link_type": "related_to",
                    "source_id": 101,
                    "destination_id": 102,
                    "is_web_link": False
                },
                { # External link associated with a source note
                    "link_type": "primary_source",
                    "source_id": 101,
                    "url": "https://example.com/source_document.pdf",
                    "is_web_link": True
                },
                { # A general web link not tied to source/destination notes here,
                  # but could be linked to a Note via Note.link_id
                    "link_type": "reference_material",
                    "url": "https://en.wikipedia.org/wiki/Knowledge_graph",
                    "is_web_link": True
                }
            ]
        }
    }

class LinkResponse(LinkBase):
    id: int
    version: int # Assuming Link model has version

    class Config:
        from_attributes = True

class LinkUpdate(BaseModel):
    link_type: Optional[str] = Field(None, max_length=255)
    destination_id: Optional[int] = None
    source_id: Optional[int] = None
    url: Optional[HttpUrl] = None # Changed to HttpUrl
    is_web_link: Optional[bool] = None
    # version: int # Version is usually handled by CRUD/DB

    model_config = { # Pydantic v2 example
        "json_schema_extra": {
            "examples": [
                {
                    "link_type": "updated_relation",
                    "url": "https://new.example.com/resource"
                }
            ]
        }
    }