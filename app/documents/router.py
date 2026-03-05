from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta, timezone
import base64

from app.db.session import get_db
from app.documents import repositories as document_repositories
from app.documents import schemas as document_schemas
from app.templates import repositories as template_repositories
from app.documents.utils.document_processor import process_docx_from_base64
from app.auth.cognito import get_current_user
from app.users.models import User
from app.config import API_URL
from app.documents.utils.token_utils import create_document_token, verify_document_token

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
    # Get the template (user-specific)
    template = template_repositories.get_template(
        db=db,
        template_id=str(document.template_id),
        user_id=current_user.cognito_user_id,
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or expired")

    # Validate template has content
    if not template.content:
        raise HTTPException(status_code=400, detail="Template content is missing")

    # Generate token (valid for 24 hours)
    token_expire_hours = 24
    expires_at = datetime.now(timezone.utc) + timedelta(hours=token_expire_hours)

    token = create_document_token(
        document_id=None,  # Will be set after creation, but not included in token
        template_id=str(document.template_id),
        user_id=current_user.cognito_user_id,
        expire_hours=token_expire_hours,
    )

    # Clean and validate base64 content before storing
    cleaned_template_content = template.content.strip()

    # Create document with template content
    db_document = document_repositories.create_document(
        db=db,
        document=document,
        user_id=current_user.cognito_user_id,
        token=token,
        template_content=cleaned_template_content,
        expires_at=expires_at,
    )

    # Build view URL
    base_url = API_URL
    view_url = f"{base_url}/documents/view?token={token}"

    return document_schemas.DocumentCreateResponse(view_url=view_url)


@router.get("/view")
def view_document_as_pdf(
    token: str = Query(..., description="Document view token"),
    db: Session = Depends(get_db),
):
    """
    View a document as PDF using its token.

    This endpoint:
    1. Validates the document token
    2. Retrieves the document from database
    3. Processes the template with the document's data
    4. Returns the generated PDF

    Authentication: Token-based (no JWT required)
    """
    # Verify token is valid
    token_payload = verify_document_token(token)
    if not token_payload:
        raise HTTPException(status_code=401, detail="Invalid or expired document token")

    # Get document by token
    document = document_repositories.get_document_by_token(db=db, token=token)
    if not document:
        raise HTTPException(
            status_code=404, detail="Document not found or token expired"
        )

    # Validate document has required data
    if not document.template:
        raise HTTPException(status_code=500, detail="Document template is missing")

    if not document.data:
        raise HTTPException(status_code=500, detail="Document data is missing")

    try:
        # Clean base64 content (remove whitespace/newlines)
        cleaned_base64 = (
            document.template.strip()
            .replace("\n", "")
            .replace("\r", "")
            .replace(" ", "")
        )

        # Test if base64 is valid and can be decoded
        try:
            decoded_bytes = base64.b64decode(cleaned_base64)
            if (
                len(decoded_bytes) < 100
            ):  # DOCX files should be at least a few hundred bytes
                raise HTTPException(
                    status_code=400,
                    detail="Document template appears to be too small or corrupted",
                )
        except Exception as decode_error:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 content in document template: {str(decode_error)}",
            )

        # Process the document: template (base64 content) + data -> PDF
        pdf_content = process_docx_from_base64(
            base64_content=cleaned_base64, data=document.data
        )

        # Return PDF as response
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=document_{document.id}.pdf"
            },
        )

    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
    except Exception as e:
        error_msg = str(e)
        if "base64" in error_msg.lower() or "zip file" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Invalid document template or corrupted base64 content",
            )
        else:
            raise HTTPException(
                status_code=500, detail=f"Document processing failed: {error_msg}"
            )
