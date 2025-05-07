# app/schemas/__init__.py
# Makes imports cleaner: from app.schemas import AppUserCreate, DocumentResponse, ...

from .user import AppUserCreate, AppUserResponse, UserUpdatePassword # Added example update schema
from .document import DocumentBase, DocumentCreate, DocumentResponse, DocumentTypeBase, DocumentTypeCreate, DocumentTypeResponse
from .note import NoteBase, NoteCreate, NoteResponse, NoteTypeBase, NoteTypeCreate, NoteTypeResponse
from .link import LinkBase, LinkCreate, LinkResponse
from .note_document import NoteDocumentBase, NoteDocumentCreate, NoteDocumentResponse
from .communication import CommunicationBase, CommunicationCreate, CommunicationResponse

# Schema for the ingestion request
from .ingestion import IngestionRequest
from .agent import AgentQueryRequest, AgentStep, AgentResponse