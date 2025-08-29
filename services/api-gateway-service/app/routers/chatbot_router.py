# app/routers/chatbot_router.py
import logging
import json
from typing import Optional, List
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, status

from ..services import chatbot_service
from ..schemas import chatbot_schemas

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/chat",
    tags=["Chatbot"]
)


# THIS IS THE CORRECT FUNCTION SIGNATURE FOR FILE UPLOADS
@router.post(
    "",
    response_model=chatbot_schemas.ChatResponse,
    operation_id="handle_chat_with_file_upload"
)
async def handle_chat_request(
        query: str = Form(...),
        history_json: str = Form("[]"),
        user_id: int = Form(1),
        web_search_enabled: bool = Form(False),
        files: List[UploadFile] = File(None)
):
    """
    Handles a user's chat message, now with multiple optional file uploads.
    """
    try:
        history_data = json.loads(history_json)
        history = [chatbot_schemas.ChatMessage.model_validate(msg) for msg in history_data]
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format for 'history_json'."
        )

    processed_files: List[chatbot_schemas.FileData] = []
    if files:
        for file in files:
            if file.filename:
                # Read the file content immediately into bytes
                content_bytes = await file.read()
                await file.close()  # Ensure the file is closed
                processed_files.append(
                    chatbot_schemas.FileData(
                        filename=file.filename,
                        content_type=file.content_type,
                        content_bytes=content_bytes
                    )
                )

    request_data = chatbot_schemas.ChatRequest(
        query=query,
        history=history,
        user_id=user_id,
        web_search_enabled=web_search_enabled
    )

    # Pass the list of files to the service layer
    return await chatbot_service.process_chat_request(request_data, processed_files)
