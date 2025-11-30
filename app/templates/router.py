from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.templates import repositories as template_repositories
from app.templates import schemas as template_schemas
from app.templates.utils.document_processor import process_docx_from_base64

router = APIRouter()
PREFIX = "/templates"


@router.post("/", response_model=template_schemas.TemplateRetrieve, status_code=201)
def create_template(
    template: template_schemas.TemplateCreate,
    db: Session = Depends(get_db),
):
    """Create a new template (permanent or temporary based on debug flag)"""
    return template_repositories.create_template(db=db, template=template)


@router.get("/{template_id}", response_model=template_schemas.TemplateRetrieve)
def get_template(template_id: UUID, db: Session = Depends(get_db)):
    """Get a template by ID (excludes expired debug records)"""
    template = template_repositories.get_template(db=db, template_id=str(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or expired")
    return template


@router.get("/", response_model=List[template_schemas.TemplateRetrieve])
def get_templates(
    include_debug: bool = Query(False, description="Include debug/temporary templates"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get templates with optional debug filtering"""
    return template_repositories.get_templates(
        db=db, include_debug=include_debug, skip=skip, limit=limit
    )


@router.delete("/{template_id}")
def delete_template(template_id: UUID, db: Session = Depends(get_db)):
    """Delete a template by ID"""
    if template_repositories.delete_template(db=db, template_id=str(template_id)):
        return {"message": "Template deleted successfully"}
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/cleanup-expired")
def cleanup_expired_debug_records(db: Session = Depends(get_db)):
    """Manual cleanup of expired debug records"""
    deleted_count = template_repositories.cleanup_expired_debug_records(db=db)
    return {"message": f"Cleaned up {deleted_count} expired debug records"}


@router.get("/view/{template_id}")
def view_template_as_pdf(template_id: UUID, db: Session = Depends(get_db)):
    """
    Process template with its data and return as PDF.

    This endpoint:
    1. Retrieves the template by ID
    2. Decodes the base64 Word document content
    3. Processes the template with the stored JSON data
    4. Converts to PDF and returns it
    """
    # Get the template from database
    template = template_repositories.get_template(db=db, template_id=str(template_id))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or expired")

    try:
        # Process the document: base64 content + JSON data -> PDF
        pdf_content = process_docx_from_base64(
            base64_content=template.content, data=template.data
        )

        # Return PDF as response
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=template_{template_id}.pdf"
            },
        )

    except Exception as e:
        error_msg = str(e)
        if "base64" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Invalid template")
        else:
            raise HTTPException(
                status_code=500, detail=f"Document processing failed: {error_msg}"
            )
