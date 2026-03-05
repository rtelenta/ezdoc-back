from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class DocumentCreate(BaseModel):
    template_id: UUID
    description: Optional[str] = None
    data: Dict[str, Any]  # Required JSON data for template processing


class DocumentRetrieve(BaseModel):
    id: UUID
    template_id: UUID
    description: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    created_by_user_id: str

    class Config:
        from_attributes = True


class DocumentCreateResponse(BaseModel):
    view_url: str
