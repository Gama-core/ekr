# app/services/notes_service.py
import logging
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status

from .. import clients
from ..schemas import note_schemas

logger = logging.getLogger(__name__)


async def get_all_notes(user_id: int) -> List[note_schemas.NoteResponse]:
    """Orchestration for getting all notes. (Simple passthrough)"""
    return await clients.database_api_client.get_notes_for_user(user_id)


async def get_note_by_id(note_id: int) -> Optional[note_schemas.NoteResponse]:
    """Orchestration for getting a single note by its ID."""
    logger.info(f"Fetching note by id: {note_id}")
    return await clients.database_api_client.get_note_by_id_from_db(note_id)


async def create_new_note(note_create: note_schemas.NoteCreateRequest, user_id: int) -> note_schemas.NoteResponse:
    """Orchestration for creating a new note."""
    logger.info(f"Orchestrating creation of new note for user_id: {user_id}")

    # Step 1: Create the note in the primary database
    payload = note_create.model_dump()
    payload['owner_id'] = user_id

    # FIX: Removed the incorrect manual renaming of 'text' to 'text_content'.
    # The database-api handles this with its Pydantic alias.
    created_note = await clients.database_api_client.create_note_in_db(payload)

    # Step 2: Trigger indexing in the semantic retrieval service
    await clients.semantic_retrieval_client.index_note(created_note.id)

    return created_note


async def update_existing_note(note_id: int, note_update: note_schemas.NoteUpdateRequest) -> note_schemas.NoteResponse:
    """Orchestration for updating a note."""
    logger.info(f"Orchestrating update for note_id: {note_id}")

    # Step 1: Update the note in the database
    payload = note_update.model_dump(exclude_unset=True)

    # FIX: Removed the incorrect manual renaming of 'text' to 'text_content'.
    # The database-api now receives the correct 'text' key.
    updated_note = await clients.database_api_client.update_note_in_db(note_id, payload)

    # Step 2: Trigger re-indexing
    await clients.semantic_retrieval_client.index_note(updated_note.id)

    return updated_note


async def delete_existing_note(note_id: int):
    """Orchestration for deleting a note."""
    logger.info(f"Orchestrating deletion for note_id: {note_id}")

    # Step 1: Delete from the database
    await clients.database_api_client.delete_note_from_db(note_id)

    # Step 2: Trigger deletion from the search index
    await clients.semantic_retrieval_client.delete_note_from_index(note_id)


async def generate_note_summary(
    note_id: int,
    summary_request: note_schemas.NoteSummaryRequest
) -> note_schemas.NoteSummaryResponse:
    """Orchestration for generating a summary for a note."""
    logger.info(f"Orchestrating summary generation for note_id: {note_id}")

    # Step 1: Fetch the note content from the database service.
    note_to_summarize = await clients.database_api_client.get_note_by_id_from_db(note_id)
    if not note_to_summarize:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # Step 2: Construct the payload for the summary service.
    # The summary service expects a specific 'note_data' structure.
    note_data_payload = {
        "title": note_to_summarize.title,
        "text_content": note_to_summarize.text,
        "sub_notes": []  # For now, we only support the 'root_only' strategy.
    }

    summary_service_payload = {
        "note_data": note_data_payload,
        "summary_level": summary_request.summary_level,
        "summary_strategy": "root_only"  # Hardcoded as it's the only one supported.
    }

    # Step 3: Call the summary service via its client.
    summary_response_data = await clients.summary_client.generate_summary_for_note(summary_service_payload)

    # Step 4: Validate and return the response using our schema.
    return note_schemas.NoteSummaryResponse.model_validate(summary_response_data)

async def fact_check_note_and_children(
    note_id: int, user_id: int
) -> note_schemas.FactCheckResponse:
    """
    Orchestrates fact-checking by fetching a note and its entire sub-note
    hierarchy, formatting it, and calling the fact-check service.
    """
    logger.info(f"Orchestrating fact-check for note tree starting at note_id: {note_id}")

    # Step 1: Fetch all notes for the user from the database.
    # This is necessary to build the complete tree structure.
    all_notes = await clients.database_api_client.get_notes_for_user(user_id)
    if not all_notes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No notes found for user.")

    # Step 2: Build the note tree starting from the requested root note_id.
    note_tree_payload = _build_note_tree_for_service(note_id, all_notes)
    if not note_tree_payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Root note with id {note_id} not found.")

    # Step 3: Construct the payload for the fact-check service.
    fact_check_service_payload = {
        "note_data": note_tree_payload,
        "check_type": "corrective_suggestions"
    }

    # Step 4: Call the fact-check service via its client.
    fact_check_data = await clients.fact_check_client.fact_check_note_data(fact_check_service_payload)

    # Step 5: Validate and return the response.
    return note_schemas.FactCheckResponse.model_validate(fact_check_data)


def _build_note_tree_for_service(
    root_id: int, all_notes: List[note_schemas.NoteResponse]
) -> Optional[Dict[str, Any]]:
    """
    Helper function to recursively build a nested dictionary representing the
    note tree, matching the structure required by the fact-check service.
    """
    note_map = {note.id: note for note in all_notes}
    if root_id not in note_map:
        return None

    # This inner function does the recursive work
    def build_node(note_id: int) -> Dict[str, Any]:
        note = note_map[note_id]
        children = [
            build_node(child.id) for child in all_notes if child.parent_id == note_id
        ]
        # This structure MUST match the 'NoteData' schema in the fact-check service
        return {
            "note_id": note.id,
            "title": note.title,
            "text_content": note.text,
            "sub_notes": children
        }

    return build_node(root_id)


async def update_note_autonomously(
        note_id: int, user_id: int
) -> note_schemas.UpdateResponse:
    """
    Orchestrates an autonomous update of a note and its children.
    """
    logger.info(f"Orchestrating AUTONOMOUS update for note tree starting at note_id: {note_id}")
    note_tree_payload = await _get_note_tree_payload(note_id, user_id)

    # Construct payload for the update service's 'autonomous' strategy
    update_service_payload = {
        "strategy": "autonomous",
        "note_data": note_tree_payload,
    }

    update_data = await clients.update_client.update_note_content(update_service_payload)
    return note_schemas.UpdateResponse.model_validate(update_data)


async def update_note_guided(
        note_id: int, user_id: int, request: note_schemas.GuidedUpdateRequest
) -> note_schemas.UpdateResponse:
    """
    Orchestrates a guided update using a user-provided list of corrections.
    """
    logger.info(f"Orchestrating GUIDED update for note tree starting at note_id: {note_id}")
    note_tree_payload = await _get_note_tree_payload(note_id, user_id)

    # Construct payload for the update service's 'guided' strategy
    update_service_payload = {
        "strategy": "guided",
        "note_data": note_tree_payload,
        "corrections_to_apply": [c.model_dump() for c in request.corrections_to_apply]
    }

    update_data = await clients.update_client.update_note_content(update_service_payload)
    return note_schemas.UpdateResponse.model_validate(update_data)


async def _get_note_tree_payload(note_id: int, user_id: int) -> Dict[str, Any]:
    """
    DRY helper to fetch all notes and build the tree structure needed by multiple services.
    """
    all_notes = await clients.database_api_client.get_notes_for_user(user_id)
    if not all_notes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No notes found for user.")

    note_tree_payload = _build_note_tree_for_service(note_id, all_notes)
    if not note_tree_payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Root note with id {note_id} not found.")

    return note_tree_payload

async def override_note_content(note_id: int, new_text: str):
    """
    Orchestrates the process of updating a note's text content in the database
    and then triggering a re-index for the search service.
    """
    logger.info(f"Orchestrating content override for note_id: {note_id}")

    # Step 1: Get the original note from the database.
    # This is important to preserve the note's original title, as the
    # AI-generated 'updated_text' often only contains the body content.
    original_note = await clients.database_api_client.get_note_by_id_from_db(note_id)
    if not original_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note to override not found.")

    # Step 2: Prepare the payload for the database update.
    # We use the original title and the new text content.
    update_payload = {
        "title": original_note.title, # Preserve the original title
        "text": new_text
    }

    # Step 3: Call the database client to update the note.
    updated_note = await clients.database_api_client.update_note_in_db(
        note_id=note_id, payload=update_payload
    )

    # Step 4: CRITICAL - Trigger re-indexing in the semantic retrieval service.
    # If we don't do this, the note will be searchable by its old content.
    await clients.semantic_retrieval_client.index_note(updated_note.id)

    logger.info(f"Successfully overrode and re-indexed note_id: {note_id}")