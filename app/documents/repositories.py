from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from app.documents.models import Document
from app.documents import schemas as document_schema
from app.templates.models import Template


def create_document(
    db: Session,
    document: document_schema.DocumentCreate,
    user_id: str,
    token: str,
    template_content: str,
    expires_at: datetime,
) -> Document:
    """Create a new document with template content and generated token"""

    db_document = Document(
        template=template_content,
        data=document.data,
        token=token,
        description=document.description,
        template_id=document.template_id,
        created_by_user_id=user_id,
        expires_at=expires_at,
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document


def get_document_by_token(db: Session, token: str) -> Optional[Document]:
    """Get a document by its token (for viewing)"""
    return (
        db.query(Document)
        .options(joinedload(Document.created_by))
        .filter(Document.token == token)
        .filter(Document.expires_at > datetime.now(timezone.utc))  # Only non-expired
        .first()
    )


def get_documents(
    db: Session, user_id: str, skip: int = 0, limit: int = 100
) -> List[Document]:
    """Get documents for a specific user (non-expired only)"""
    return (
        db.query(Document)
        .options(joinedload(Document.created_by))
        .filter(Document.created_by_user_id == user_id)
        .filter(Document.expires_at > datetime.now(timezone.utc))  # Only non-expired
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
