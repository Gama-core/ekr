# app/models/__init__.py
# Makes imports cleaner: from app.models import AppUser, Document, ...

from .user import AppUser
from .document import Document, DocumentType
from .note import Note, NoteType
from .link import Link
from .note_document import NoteDocument
from .communication import Communication