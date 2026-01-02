from sqlalchemy import Column, Text, Boolean, DateTime, JSON, String, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
    )
    name = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Base64 encoded Word file
    data = Column(JSON, nullable=False)  # JSON with flexible structure
    debug = Column(Boolean, default=False, nullable=False, index=True)
    created_by_user_id = Column(
        String, ForeignKey("users.cognito_user_id"), nullable=False, index=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Only for debug records

    # Relationship to User
    created_by = relationship("User", foreign_keys=[created_by_user_id])
