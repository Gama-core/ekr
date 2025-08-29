# app/clients/ocr_client.py
import logging
from typing import Optional
from ..schemas.chatbot_schemas import FileData

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


async def process_uploaded_file(file_data: FileData) -> Optional[str]:
    """
    Sends file bytes, which have already been read in the router, to the OCR service
    and returns the extracted text.
    """
    url = f"{settings.OCR_API_URL}/upload"

    # The payload is built directly from the bytes and metadata in the FileData object.
    files = {'file': (file_data.filename, file_data.content_bytes, file_data.content_type)}

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, files=files)
            response.raise_for_status()

            response_data = response.json()
            if response_data.get("status") == "success":
                # FIX: Use the correct 'markdown' key from the ocr-service response.
                all_pages_content = [p.get("markdown", "") for p in response_data.get("pages", [])]
                full_text = "\n\n".join(all_pages_content)
                logger.info(f"Successfully performed OCR on file: {file_data.filename}")
                return full_text
            else:
                error_msg = response_data.get("error_message", "Unknown OCR error")
                logger.error(f"OCR service failed for file {file_data.filename}: {error_msg}")
                return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling OCR service for {file_data.filename}: {e.response.text}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Could not connect to OCR Service at {url}: {e}")
        return None