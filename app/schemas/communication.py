# app/schemas/communication.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CommunicationBase(BaseModel):
    title: str = Field(..., max_length=255)
    text: str # Consider max length or different type if needed
    publication_start_date: datetime
    publication_end_date: Optional[datetime] = None
    image_id: Optional[int] = None # ID of a related Document
    created_by_id: int # Usually set from context
    external: Optional[bool] = False


class CommunicationCreate(CommunicationBase):
    # version is usually handled by DB/ORM
    version: Optional[int] = 0
    # creation_date is usually set automatically
    creation_date: Optional[datetime] = None
     # created_by_id usually set from context
    created_by_id: Optional[int] = None


class CommunicationResponse(CommunicationBase):
    id: int
    version: int
    creation_date: datetime # Include if needed

    class Config:
        from_attributes = True