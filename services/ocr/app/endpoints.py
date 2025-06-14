import logging
from fastapi import APIRouter, HTTPException, status, UploadFile, File

from .schemas import OcrUrlRequest, OcrServiceResponse
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/url", response_model=OcrServiceResponse, summary="Perform OCR on a URL")
async def ocr_from_url(request: OcrUrlRequest):
    """Processes a document or image from a public URL using Mistral AI OCR."""
    try:
        result = await service.perform_ocr_on_url(str(request.url))
        if result.status == "failed":
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.error_message)
        return result
    except Exception as e:
        logger.exception(f"Unexpected error in /url endpoint for URL '{request.url}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An unexpected server error occurred: {e}")


@router.post("/upload", response_model=OcrServiceResponse, summary="Perform OCR on an Uploaded File")
async def ocr_from_upload(file: UploadFile = File(...)):
    """Processes a directly uploaded PDF or image file using Mistral AI OCR."""
    if not file.content_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine file content type.")

    try:
        result = await service.perform_ocr_on_upload(file)
        if result.status == "failed":
            if "Unsupported content type" in (result.error_message or ""):
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=result.error_message)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.error_message)
        return result
    except Exception as e:
        logger.exception(f"Unexpected error in /upload endpoint for file '{file.filename}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An unexpected server error occurred: {e}")