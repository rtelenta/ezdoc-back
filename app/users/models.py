from sqlalchemy import Column, String, Text, DateTime, func
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # Primary key - Cognito user ID (the 'sub' claim from JWT)
    cognito_user_id = Column(String, primary_key=True)

    # Basic user information (cached from Cognito for quick access)
    email = Column(String, nullable=False, unique=True, index=True)
    full_name = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(cognito_user_id={self.cognito_user_id}, email={self.email})>"
