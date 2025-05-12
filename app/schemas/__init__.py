# app/schemas/__init__.py
# Makes imports cleaner: from app.schemas import AppUserCreate, DocumentResponse, ...

from .document import (
    DocumentBase, DocumentCreate, DocumentResponse, DocumentUpdate, # Added DocumentUpdate
    DocumentTypeBase, DocumentTypeCreate, DocumentTypeResponse, DocumentTypeUpdate # Added DocumentTypeUpdate
)
from .note import (
    NoteBase, NoteCreate, NoteResponse, NoteUpdate, # Added NoteUpdate
    NoteTypeBase, NoteTypeCreate, NoteTypeResponse, NoteTypeUpdate # Added NoteTypeUpdate
)
from .user import AppUserCreate, AppUserResponse, AppUserUpdate, UserUpdatePassword # Added AppUserUpdate
from .link import LinkBase, LinkCreate, LinkResponse, LinkUpdate # Added LinkUpdate
from .ingestion import IngestionRequest, ProcessedUrlResult, IngestionResponse # Added ProcessedUrlResult
from .assistant import AssistantQueryRequest, Source, AssistantResponse # Added Assistant Schemas
from .communication import CommunicationBase, CommunicationCreate, CommunicationResponse # Assuming these exist
from .note_document import NoteDocumentBase, NoteDocumentCreate, NoteDocumentResponse # Assuming these exist


