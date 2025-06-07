# app/features/ocr/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class OcrUrlRequest(BaseModel):
    url: HttpUrl = Field(..., description="The URL of the document (PDF) or image to process with OCR.")

class OcrPage(BaseModel):
    page_index: int = Field(..., alias="index", description="The page index in the document, starting from 0.")
    markdown_content: str = Field(..., alias="markdown", description="The full markdown text extracted from the page.")

    class Config:
        populate_by_name = True

class OcrUsage(BaseModel):
    pages_processed: int = Field(..., description="The number of pages processed in the request.")
    doc_size_bytes: Optional[int] = Field(None, description="The size of the document in bytes.")

class OcrServiceResponse(BaseModel):
    status: str = Field(..., description="Status of the OCR operation (e.g., 'success', 'failed').")
    model_used: Optional[str] = Field(None, description="The OCR model that processed the request.")
    pages: List[OcrPage] = Field([], description="List of processed pages with their markdown content.")
    usage: Optional[OcrUsage] = Field(None, description="Usage information for the OCR request.")
    error_message: Optional[str] = Field(None, description="Error message if the OCR process failed.")