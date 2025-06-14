# services/database-api/app/models.py
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime

class Base(DeclarativeBase):
    pass


class AppUser(Base):
    __tablename__ = 'app_user'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='app_user_pkey'),
        Index('ix_app_user_email', 'email'),
        Index('ix_app_user_id', 'id'),
        Index('ix_app_user_username', 'username', unique=True)
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[int] = mapped_column(Integer)
    phone: Mapped[Optional[str]] = mapped_column(String(200))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_birth: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    email: Mapped[Optional[str]] = mapped_column(String(255))

    note: Mapped[List['Note']] = relationship('Note', back_populates='owner')
    document: Mapped[List['Document']] = relationship('Document', back_populates='owned_by')
    communication: Mapped[List['Communication']] = relationship('Communication', back_populates='created_by')


class DocumentType(Base):
    __tablename__ = 'document_type'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='document_type_pkey'),
        Index('ix_document_type_id', 'id')
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(255))

    document: Mapped[List['Document']] = relationship('Document', back_populates='doc_type')


class Link(Base):
    __tablename__ = 'link'
    __table_args__ = (
        ForeignKeyConstraint(['destination_id'], ['note.id'], name='fk1xhxb20vxll7wef2b959a0t43'),
        ForeignKeyConstraint(['source_id'], ['note.id'], name='fk5ng2f8qo1qa8ydkbb01xui55u'),
        PrimaryKeyConstraint('id', name='link_pkey'),
        Index('ix_link_destination_id', 'destination_id'),
        Index('ix_link_id', 'id'),
        Index('ix_link_source_id', 'source_id')
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    link_type: Mapped[Optional[str]] = mapped_column(String(255))
    destination_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    source_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    url: Mapped[Optional[str]] = mapped_column(String(255))
    is_web_link: Mapped[Optional[bool]] = mapped_column(Boolean)

    destination: Mapped[Optional['Note']] = relationship('Note', foreign_keys=[destination_id], back_populates='link')
    source: Mapped[Optional['Note']] = relationship('Note', foreign_keys=[source_id], back_populates='link_')
    note: Mapped[List['Note']] = relationship('Note', foreign_keys='[Note.link_id]', back_populates='link1')


class Note(Base):
    __tablename__ = 'note'
    __table_args__ = (
        ForeignKeyConstraint(['link_id'], ['link.id'], name='fkiworc5kmsn9utqtg9urf630v4'),
        ForeignKeyConstraint(['owner_id'], ['app_user.id'], name='fkjl54w6uv8owox1s3dqb0w4r0y'),
        ForeignKeyConstraint(['parent_id'], ['note.id'], name='fkdenwvx1lpx4tcd91ip240bgmx'),
        ForeignKeyConstraint(['type_id'], ['note_type.id'], name='fk9527dlwrq1xicouxhg2s2sfv1'),
        PrimaryKeyConstraint('id', name='note_pkey'),
        Index('ix_note_id', 'id'),
        Index('ix_note_owner_id', 'owner_id'),
        Index('ix_note_parent_id', 'parent_id'),
        Index('ix_note_type_id', 'type_id')
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    owner_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(255))
    text: Mapped[Optional[str]] = mapped_column(String(4000))
    type_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    creation_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    link_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    color: Mapped[Optional[str]] = mapped_column(String(255))

    link: Mapped[List['Link']] = relationship('Link', foreign_keys='[Link.destination_id]', back_populates='destination')
    link_: Mapped[List['Link']] = relationship('Link', foreign_keys='[Link.source_id]', back_populates='source')
    link1: Mapped[Optional['Link']] = relationship('Link', foreign_keys=[link_id], back_populates='note')
    owner: Mapped['AppUser'] = relationship('AppUser', back_populates='note')
    parent: Mapped[Optional['Note']] = relationship('Note', remote_side=[id], back_populates='parent_reverse')
    parent_reverse: Mapped[List['Note']] = relationship('Note', remote_side=[parent_id], back_populates='parent')
    type: Mapped[Optional['NoteType']] = relationship('NoteType', back_populates='note')
    document: Mapped[List['Document']] = relationship('Document', secondary='note_document', back_populates='note_documents')


class NoteType(Base):
    __tablename__ = 'note_type'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='note_type_pkey'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(255))

    note: Mapped[List['Note']] = relationship('Note', back_populates='type')


class Document(Base):
    __tablename__ = 'document'
    __table_args__ = (
        ForeignKeyConstraint(['doc_type_id'], ['document_type.id'], name='fk2k76h74qjtj2x01y6b65lhhe5'),
        ForeignKeyConstraint(['owned_by_id'], ['app_user.id'], name='fkohc6bp152gc8n48yslp28w2h1'),
        PrimaryKeyConstraint('id', name='document_pkey'),
        Index('ix_document_doc_type_id', 'doc_type_id'),
        Index('ix_document_id', 'id'),
        Index('ix_document_owned_by_id', 'owned_by_id')
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    doc_type_id: Mapped[int] = mapped_column(BigInteger)
    path: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    comment: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(255))
    owned_by_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    url: Mapped[Optional[str]] = mapped_column(String(255))

    doc_type: Mapped['DocumentType'] = relationship('DocumentType', back_populates='document')
    owned_by: Mapped[Optional['AppUser']] = relationship('AppUser', back_populates='document')
    note_documents: Mapped[List['Note']] = relationship('Note', secondary='note_document', back_populates='document')
    communication: Mapped[List['Communication']] = relationship('Communication', back_populates='image')


class Communication(Base):
    __tablename__ = 'communication'
    __table_args__ = (
        ForeignKeyConstraint(['created_by_id'], ['app_user.id'], name='fk5y9ggcnbng969seo00gapl10v'),
        ForeignKeyConstraint(['image_id'], ['document.id'], name='fk5s5wloj7m65tm3jxwivaus7ah'),
        PrimaryKeyConstraint('id', name='communication_pkey'),
        Index('ix_communication_created_by_id', 'created_by_id'),
        Index('ix_communication_id', 'id')
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(255))
    publication_start_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    creation_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    created_by_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(String(255))
    publication_end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    image_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    external: Mapped[Optional[bool]] = mapped_column(Boolean)

    created_by: Mapped['AppUser'] = relationship('AppUser', back_populates='communication')
    image: Mapped[Optional['Document']] = relationship('Document', back_populates='communication')


t_note_document = Table(
    'note_document', Base.metadata,
    Column('note_documents_id', BigInteger, nullable=False),
    Column('document_id', BigInteger),
    ForeignKeyConstraint(['document_id'], ['document.id'], name='fktcdodp79xgi30su87vlqk8mol'),
    ForeignKeyConstraint(['note_documents_id'], ['note.id'], name='fkctbfk20tb81ov7qf8tf32w6wn')
)
