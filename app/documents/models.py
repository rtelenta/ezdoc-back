from sqlalchemy import Column, Text, DateTime, JSON, String, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
    )
    template = Column(
        Text, nullable=False
    )  # Base64 encoded Word file (copied from Template)
    data = Column(JSON, nullable=False)  # JSON data for template processing
    token = Column(
        String(500), nullable=False, unique=True, index=True
    )  # Generated view token
    description = Column(Text, nullable=True)  # Optional description

    # Reference to original template
    template_id = Column(
        UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False, index=True
    )

    # User tracking
    created_by_user_id = Column(
        String, ForeignKey("users.cognito_user_id"), nullable=False, index=True
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(
        DateTime(timezone=True), nullable=False, index=True
    )  # Token expiration

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    template_ref = relationship("Template", foreign_keys=[template_id])
