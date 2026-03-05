from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class UserInfo(BaseModel):
    """User information embedded in template response"""

    cognito_user_id: str
    email: str
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    name: str  # Template name
    content: str  # Base64 encoded Word file content
    data: Optional[Dict[str, Any]] = None  # Flexible JSON structure
    debug: bool = False
    expire_hours: Optional[int] = 2  # Only used when debug=True


class TemplateRetrieve(BaseModel):
    id: UUID
    name: str
    debug: bool
    created_by: UserInfo  # Nested user information
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    debug: Optional[bool] = None
    expire_hours: Optional[int] = None
