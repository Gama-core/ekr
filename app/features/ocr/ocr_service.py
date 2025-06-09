# app/features/ocr/ocr_service.py
import logging
import httpx
from typing import Optional, Dict, Any
import base64
from fastapi import UploadFile

# Core and feature imports
from app.core.config import settings as core_settings
from app.features.ocr.config import ocr_settings
from app.features.ocr.schemas import OcrServiceResponse, OcrPage, OcrUsage

logger = logging.getLogger(__name__)

async def _call_mistral_ocr_api(client: httpx.AsyncClient, payload: Dict[str, Any]) -> httpx.Response:
    """Helper function to make the actual API call to Mistral OCR."""
    headers = {
        "Authorization": f"Bearer {core_settings.MISTRAL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    api_url = f"{core_settings.MISTRAL_API_BASE_URL}/v1/ocr"

    logger.debug(f"Calling Mistral OCR API at {api_url} with document type '{payload['document']['type']}' for URL {payload['document'].get('document_url') or payload['document'].get('image_url')}")

    response = await client.post(
        api_url,
        json=payload,
        headers=headers,
        timeout=ocr_settings.OCR_TIMEOUT_SECONDS
    )
    return response

async def perform_ocr_on_url(url: str) -> OcrServiceResponse:
    """
    Performs OCR on a given URL, attempting PDF and then Image processing, as shown in Mistral cookbooks.
    """
    async with httpx.AsyncClient() as client:
        try:
            # First, try as a PDF document
            pdf_payload = {
                "model": core_settings.MISTRAL_OCR_DEFAULT_MODEL,
                "document": {"type": "document_url", "document_url": url}
            }
            response = await _call_mistral_ocr_api(client, pdf_payload)
            response.raise_for_status()  # Raise exception for 4xx/5xx responses
        except (httpx.HTTPStatusError, httpx.RequestError) as e_pdf:
            logger.warning(f"Mistral OCR for URL '{url}' as 'document_url' failed: {e_pdf}. Trying as 'image_url'.")
            try:
                # If PDF fails, try as an Image
                image_payload = {
                    "model": core_settings.MISTRAL_OCR_DEFAULT_MODEL,
                    "document": {"type": "image_url", "image_url": url}
                }
                response = await _call_mistral_ocr_api(client, image_payload)
                response.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as e_img:
                error_msg = f"Mistral OCR failed for URL '{url}' as both document and image. Final error: {e_img}"
                logger.error(error_msg)
                return OcrServiceResponse(status="failed", error_message=error_msg)
            except Exception as e_unhandled_img:
                error_msg = f"An unexpected error occurred during image OCR for '{url}': {e_unhandled_img}"
                logger.exception(error_msg)
                return OcrServiceResponse(status="failed", error_message=error_msg)

    # If we get here, one of the calls was successful
    try:
        data = response.json()

        pages = [OcrPage.model_validate(p) for p in data.get("pages", [])]

        usage_data = data.get("usage_info")
        usage = OcrUsage.model_validate(usage_data) if usage_data else None

        return OcrServiceResponse(
            status="success",
            model_used=data.get("model"),
            pages=pages,
            usage=usage
        )
    except Exception as e_parse:
        error_msg = f"Failed to parse successful response from Mistral OCR for '{url}': {e_parse}"
        logger.exception(error_msg)
        return OcrServiceResponse(status="failed", error_message=error_msg)


async def perform_ocr_on_upload(file: UploadFile) -> OcrServiceResponse:
    """
    Performs OCR on a directly uploaded file by encoding it to base64.
    """
    try:
        file_bytes = await file.read()
        if not file_bytes:
            return OcrServiceResponse(status="failed", error_message="Uploaded file is empty.")
    except Exception as e:
        logger.error(f"Failed to read bytes from uploaded file '{file.filename}': {e}")
        return OcrServiceResponse(status="failed", error_message=f"Failed to read uploaded file: {e}")
    finally:
        await file.close()

    base64_encoded_content = base64.b64encode(file_bytes).decode('utf-8')
    content_type = file.content_type

    payload = {"model": core_settings.MISTRAL_OCR_DEFAULT_MODEL}
    if content_type == "application/pdf":
        data_uri = f"data:application/pdf;base64,{base64_encoded_content}"
        # Per Mistral docs, use 'document_url' for base64 encoded PDFs
        payload["document"] = {"type": "document_url", "document_url": data_uri}
    elif content_type and content_type.startswith("image/"):
        data_uri = f"data:{content_type};base64,{base64_encoded_content}"
        # Per Mistral docs, use 'image_url' for base64 encoded images
        payload["document"] = {"type": "image_url", "image_url": data_uri}
    else:
        error_msg = f"Unsupported content type: '{content_type}'. Please upload a PDF or a standard image file."
        logger.warning(error_msg)
        return OcrServiceResponse(status="failed", error_message=error_msg)

    async with httpx.AsyncClient() as client:
        try:
            response = await _call_mistral_ocr_api(client, payload)
            response.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            error_msg = f"Mistral OCR failed for uploaded file '{file.filename}'. Error: {e}"
            logger.error(error_msg)
            return OcrServiceResponse(status="failed", error_message=error_msg)
        except Exception as e_unhandled:
            error_msg = f"An unexpected error occurred during OCR for uploaded file '{file.filename}': {e_unhandled}"
            logger.exception(error_msg)
            return OcrServiceResponse(status="failed", error_message=error_msg)

    try:
        data = response.json()
        pages = [OcrPage.model_validate(p) for p in data.get("pages", [])]
        usage_data = data.get("usage_info")
        usage = OcrUsage.model_validate(usage_data) if usage_data else None

        return OcrServiceResponse(
            status="success",
            model_used=data.get("model"),
            pages=pages,
            usage=usage
        )
    except Exception as e_parse:
        error_msg = f"Failed to parse successful response from Mistral OCR for uploaded file '{file.filename}': {e_parse}"
        logger.exception(error_msg)
        return OcrServiceResponse(status="failed", error_message=error_msg)