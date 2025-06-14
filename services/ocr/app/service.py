import logging
import httpx
from typing import Dict, Any
import base64
from fastapi import UploadFile

from .config import settings
from .schemas import OcrServiceResponse, OcrPage, OcrUsage

logger = logging.getLogger(__name__)

async def _call_mistral_ocr_api(client: httpx.AsyncClient, payload: Dict[str, Any]) -> httpx.Response:
    """Helper function to make the actual API call to Mistral OCR."""
    if not settings.MISTRAL_API_KEY:
        raise ValueError("Mistral API key is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.MISTRAL_API_KEY.get_secret_value()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    api_url = f"{settings.MISTRAL_API_BASE_URL}/v1/ocr"

    return await client.post(
        api_url,
        json=payload,
        headers=headers,
        timeout=settings.OCR_TIMEOUT_SECONDS
    )

def _parse_successful_response(response_data: dict) -> OcrServiceResponse:
    """Parses a successful JSON response from the API into our schema."""
    pages = [OcrPage.model_validate(p) for p in response_data.get("pages", [])]
    usage_data = response_data.get("usage_info")
    usage = OcrUsage.model_validate(usage_data) if usage_data else None
    return OcrServiceResponse(
        status="success",
        model_used=response_data.get("model"),
        pages=pages,
        usage=usage
    )

async def perform_ocr_on_url(url: str) -> OcrServiceResponse:
    """Performs OCR on a URL, trying both PDF and image endpoints."""
    async with httpx.AsyncClient() as client:
        try:
            # First, try as a PDF document
            pdf_payload = {"model": settings.MISTRAL_OCR_DEFAULT_MODEL, "document": {"type": "document_url", "document_url": url}}
            response = await _call_mistral_ocr_api(client, pdf_payload)
            response.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as e_pdf:
            logger.warning(f"OCR for URL '{url}' as 'document' failed: {e_pdf}. Trying as 'image'.")
            try:
                # If PDF fails, try as an Image
                image_payload = {"model": settings.MISTRAL_OCR_DEFAULT_MODEL, "document": {"type": "image_url", "image_url": url}}
                response = await _call_mistral_ocr_api(client, image_payload)
                response.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as e_img:
                error_msg = f"Mistral OCR failed for URL '{url}' as both document and image. Final error: {e_img}"
                logger.error(error_msg)
                return OcrServiceResponse(status="failed", error_message=error_msg)
            except Exception as e:
                return OcrServiceResponse(status="failed", error_message=f"An unexpected error occurred: {e}")

    try:
        return _parse_successful_response(response.json())
    except Exception as e_parse:
        return OcrServiceResponse(status="failed", error_message=f"Failed to parse successful API response: {e_parse}")

async def perform_ocr_on_upload(file: UploadFile) -> OcrServiceResponse:
    """Performs OCR on a directly uploaded file."""
    try:
        file_bytes = await file.read()
        if not file_bytes:
            return OcrServiceResponse(status="failed", error_message="Uploaded file is empty.")
    finally:
        await file.close()

    base64_content = base64.b64encode(file_bytes).decode('utf-8')
    content_type = file.content_type
    payload = {"model": settings.MISTRAL_OCR_DEFAULT_MODEL}

    if content_type == "application/pdf":
        data_uri = f"data:application/pdf;base64,{base64_content}"
        payload["document"] = {"type": "document_url", "document_url": data_uri}
    elif content_type and content_type.startswith("image/"):
        data_uri = f"data:{content_type};base64,{base64_content}"
        payload["document"] = {"type": "image_url", "image_url": data_uri}
    else:
        return OcrServiceResponse(status="failed", error_message=f"Unsupported content type: '{content_type}'.")

    async with httpx.AsyncClient() as client:
        try:
            response = await _call_mistral_ocr_api(client, payload)
            response.raise_for_status()
            return _parse_successful_response(response.json())
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            return OcrServiceResponse(status="failed", error_message=f"Mistral OCR API error: {e}")
        except Exception as e:
            return OcrServiceResponse(status="failed", error_message=f"An unexpected error occurred: {e}")