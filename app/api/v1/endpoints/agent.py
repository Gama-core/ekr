# app/api/v1/endpoints/agent.py
import logging
from fastapi import APIRouter, HTTPException, status
from app import schemas
from app.services import agent_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/query",
    response_model=schemas.agent.AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Process User Query with Web Context",
    description="""
Takes a user's query, uses an LLM to determine what to search for,
searches the web, crawls the top result for context, and then uses
another LLM call to answer the original query based on the context.
""",
    tags=["V1 - Agent Query"] # Ensure tag matches main.py
)
async def process_agent_query(
    request: schemas.agent.AgentQueryRequest
) -> schemas.agent.AgentResponse:
    if not request.user_query or not request.user_query.strip():
        logger.warning("Received empty user query.")
        raise HTTPException(status_code=400, detail="User query cannot be empty.")
    logger.info(f"Received agent query request: '{request.user_query}'")
    try:
        response = await agent_service.process_user_query_with_web_context(
            user_query=request.user_query
        )
        return response
    except Exception as e:
        logger.exception(f"Unhandled exception in /agent/query endpoint for query: {request.user_query}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {str(e)}"
        )