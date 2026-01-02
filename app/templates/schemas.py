from typing import Optional, Dict, Any
from pydantic import BaseModel, computed_field
from datetime import datetime
from uuid import UUID
from app.config import API_URL


class TemplateCreate(BaseModel):
    content: str  # Base64 encoded Word file content
    data: Dict[str, Any]  # Flexible JSON structure
    debug: bool = False
    expire_hours: Optional[int] = 2  # Only used when debug=True


class TemplateRetrieve(BaseModel):
    id: UUID
    debug: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    @computed_field
    @property
    def view_link(self) -> str:
        """Generate view link using API_URL + /view/ + template_id"""
        base_url = API_URL

        return f"{base_url}/templates/view/{self.id}"

    class Config:
        from_attributes = True


class TemplateUpdate(BaseModel):
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    debug: Optional[bool] = None
    expire_hours: Optional[int] = None
