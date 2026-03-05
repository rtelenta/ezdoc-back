from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.templates import repositories as template_repositories
from app.templates import schemas as template_schemas
from app.auth.cognito import get_current_user
from app.users.models import User

router = APIRouter()
PREFIX = "/templates"


@router.post("/", response_model=template_schemas.TemplateRetrieve, status_code=201)
def create_template(
    template: template_schemas.TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new template (permanent or temporary based on debug flag)"""
    # User is automatically authenticated and created in DB on first request
    return template_repositories.create_template(
        db=db, template=template, user_id=current_user.cognito_user_id
    )


@router.get("/{template_id}", response_model=template_schemas.TemplateRetrieve)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a template by ID (excludes expired debug records, user-specific)"""
    template = template_repositories.get_template(
        db=db, template_id=str(template_id), user_id=current_user.cognito_user_id
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or expired")
    return template


@router.get("/", response_model=List[template_schemas.TemplateRetrieve])
def get_templates(
    include_debug: bool = Query(False, description="Include debug/temporary templates"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get templates with optional debug filtering (user-specific)"""
    return template_repositories.get_templates(
        db=db,
        user_id=current_user.cognito_user_id,
        include_debug=include_debug,
        skip=skip,
        limit=limit,
    )


@router.delete("/{template_id}")
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a template by ID (user-specific)"""
    if template_repositories.delete_template(
        db=db, template_id=str(template_id), user_id=current_user.cognito_user_id
    ):
        return {"message": "Template deleted successfully"}
    raise HTTPException(status_code=404, detail="Template not found")
