from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class OcrUrlRequest(BaseModel):
    url: HttpUrl

class OcrPage(BaseModel):
    page_index: int = Field(..., alias="index")
    markdown_content: str = Field(..., alias="markdown")

    class Config:
        populate_by_name = True
        from_attributes = True

class OcrUsage(BaseModel):
    pages_processed: int
    doc_size_bytes: Optional[int] = None


class OcrServiceResponse(BaseModel):
    status: str
    model_used: Optional[str] = None
    pages: List[OcrPage] = []
    usage: Optional[OcrUsage] = None
    error_message: Optional[str] = None