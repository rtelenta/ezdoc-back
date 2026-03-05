from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.documents import repositories as document_repositories
from app.documents import schemas as document_schemas
from app.templates import repositories as template_repositories
from app.auth.cognito import get_current_user
from app.users.models import User
from app.config import API_URL
from app.documents.utils.token_utils import create_document_token

router = APIRouter()
PREFIX = "/documents"


@router.post(
    "/", response_model=document_schemas.DocumentCreateResponse, status_code=201
)
def create_document(
    document: document_schemas.DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new document from a template.

    This endpoint:
    1. Retrieves the template content by template_id
    2. Generates a unique view token for the document
    3. Stores the document with template content, data, and token
    4. Returns a view URL with the token
    """
    # Get the template
    template = template_repositories.get_template(
        db=db, template_id=str(document.template_id)
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or expired")

    # Generate token (valid for 24 hours)
    token_expire_hours = 24
    expires_at = datetime.now(timezone.utc) + timedelta(hours=token_expire_hours)

    token = create_document_token(
        document_id=None,  # Will be set after creation, but not included in token
        template_id=str(document.template_id),
        user_id=current_user.cognito_user_id,
        expire_hours=token_expire_hours,
    )

    # Create document with template content
    db_document = document_repositories.create_document(
        db=db,
        document=document,
        user_id=current_user.cognito_user_id,
        token=token,
        template_content=template.content,
        expires_at=expires_at,
    )

    # Build view URL
    base_url = API_URL
    view_url = f"{base_url}/documents/view?token={token}"

    return document_schemas.DocumentCreateResponse(view_url=view_url)
