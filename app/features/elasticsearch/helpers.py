def build_es_document(note):
    """
    Convert a SQLAlchemy Note object into a dictionary for Elasticsearch indexing.
    """
    return {
        "note_id": note.id,
        "title": note.title,
        "text": note.text,
        "color": note.color,
        "owner_id": note.owner_id,
        "type_id": note.type_id,
        "creation_date": note.creation_date.isoformat() if note.creation_date else None,
        "parent_note_id": note.parent_id,
        "link_id": note.link_id
    }
