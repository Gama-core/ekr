# app/features/ocr/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status, UploadFile, File

from app.features.ocr.schemas import OcrUrlRequest, OcrServiceResponse
from app.features.ocr import ocr_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/url",
    response_model=OcrServiceResponse,
    summary="Perform OCR on a Document or Image from a URL",
    description="Takes a public URL to a PDF or image file, performs OCR using Mistral AI, and returns the extracted markdown content.",
    tags=["V1 - OCR"]
)
async def ocr_from_url(request: OcrUrlRequest):
    try:
        result = await ocr_service.perform_ocr_on_url(str(request.url))

        if result.status == "failed":
            # Use 502 for upstream API failures, 500 for parsing/internal errors.
            error_code = status.HTTP_502_BAD_GATEWAY if "Mistral OCR failed" in (result.error_message or "") else status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(
                status_code=error_code,
                detail=result.error_message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /ocr/url endpoint for URL '{request.url}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}"
        )


@router.post(
    "/upload",
    response_model=OcrServiceResponse,
    summary="Perform OCR on a Directly Uploaded File",
    description="Upload a PDF or image file directly to perform OCR using Mistral AI and returns the extracted markdown content.",
    tags=["V1 - OCR"]
)
async def ocr_from_upload(file: UploadFile = File(...)):
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine content type of the uploaded file."
        )

    try:
        result = await ocr_service.perform_ocr_on_upload(file)

        if result.status == "failed":
            if "Unsupported content type" in (result.error_message or ""):
                error_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            elif "Mistral OCR failed" in (result.error_message or ""):
                error_code = status.HTTP_502_BAD_GATEWAY
            else:
                error_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(
                status_code=error_code,
                detail=result.error_message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /ocr/upload endpoint for file '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}"
        )