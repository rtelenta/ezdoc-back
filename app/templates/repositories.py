from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.templates.models import Template
from app.templates import schemas as template_schema


def create_template(db: Session, template: template_schema.TemplateCreate) -> Template:
    """Create a new template (permanent or temporary based on debug flag)"""
    expires_at = None
    if template.debug:
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=template.expire_hours or 2
        )

    db_template = Template(
        content=template.content,
        data=template.data,
        debug=template.debug,
        expires_at=expires_at,
    )

    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


def get_template(db: Session, template_id: str) -> Optional[Template]:
    """Get a template by ID, excluding expired debug records"""
    query = db.query(Template).filter(Template.id == template_id)

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
    db: Session, include_debug: bool = False, skip: int = 0, limit: int = 100
) -> List[Template]:
    """Get templates with optional debug filtering"""
    query = db.query(Template)

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


def delete_template(db: Session, template_id: str) -> bool:
    """Delete a template by ID"""
    template = db.query(Template).filter(Template.id == template_id).first()
    if template:
        db.delete(template)
        db.commit()
        return True
    return False
