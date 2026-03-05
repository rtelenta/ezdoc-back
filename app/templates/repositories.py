from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.templates.models import Template
from app.templates import schemas as template_schema


def create_template(
    db: Session, template: template_schema.TemplateCreate, user_id: str
) -> Template:
    """Create a new template (permanent or temporary based on debug flag)"""
    expires_at = None
    if template.debug:
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=template.expire_hours or 2
        )

    db_template = Template(
        name=template.name,
        content=template.content,
        data=template.data,
        debug=template.debug,
        created_by_user_id=user_id,
        expires_at=expires_at,
    )

    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    # Eagerly load the created_by relationship
    db_template = (
        db.query(Template)
        .options(joinedload(Template.created_by))
        .filter(Template.id == db_template.id)
        .first()
    )
    return db_template


def get_template(db: Session, template_id: str, user_id: str) -> Optional[Template]:
    """Get a template by ID for a specific user, excluding expired debug records"""
    query = (
        db.query(Template)
        .options(joinedload(Template.created_by))
        .filter(Template.id == template_id)
        .filter(Template.created_by_user_id == user_id)  # Filter by user
    )

    # Add expiration filter for debug records
    query = query.filter(
        or_(
            Template.debug == False,  # Permanent records
            and_(
                Template.debug == True,
                Template.expires_at
                > datetime.now(timezone.utc),  # Non-expired debug records
            ),
        )
    )

    return query.first()


def get_templates(
    db: Session,
    user_id: str,
    include_debug: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Template]:
    """Get templates for a specific user with optional debug filtering"""
    query = db.query(Template).options(joinedload(Template.created_by))

    # Filter by user
    query = query.filter(Template.created_by_user_id == user_id)

    if not include_debug:
        # Only permanent records
        query = query.filter(Template.debug == False)
    else:
        # Include debug records but filter expired ones
        query = query.filter(
            or_(
                Template.debug == False,
                and_(
                    Template.debug == True,
                    Template.expires_at > datetime.now(timezone.utc),
                ),
            )
        )

    return query.offset(skip).limit(limit).all()


def cleanup_expired_debug_records(db: Session) -> int:
    """Clean up expired debug records. Returns count of deleted records."""
    expired_count = (
        db.query(Template)
        .filter(
            and_(
                Template.debug == True,
                Template.expires_at <= datetime.now(timezone.utc),
            )
        )
        .delete(synchronize_session=False)
    )

    db.commit()
    return expired_count


def delete_template(db: Session, template_id: str, user_id: str) -> bool:
    """Delete a template by ID for a specific user. Returns True if deleted, False if not found."""
    template = (
        db.query(Template)
        .filter(Template.id == template_id)
        .filter(
            Template.created_by_user_id == user_id
        )  # Only allow deleting own templates
        .first()
    )
    if template:
        db.delete(template)
        db.commit()
        return True
    return False
