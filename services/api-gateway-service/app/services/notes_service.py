# app/services/notes_service.py
import logging
from typing import List, Optional

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

    if 'text' in payload:
        payload['text_content'] = payload.pop('text')

    created_note = await clients.database_api_client.create_note_in_db(payload)

    # Step 2: Trigger indexing in the semantic retrieval service
    await clients.semantic_retrieval_client.index_note(created_note.id)

    return created_note


async def update_existing_note(note_id: int, note_update: note_schemas.NoteUpdateRequest) -> note_schemas.NoteResponse:
    """Orchestration for updating a note."""
    logger.info(f"Orchestrating update for note_id: {note_id}")

    # Step 1: Update the note in the database
    payload = note_update.model_dump(exclude_unset=True)
    if 'text' in payload:
        payload['text_content'] = payload.pop('text')

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