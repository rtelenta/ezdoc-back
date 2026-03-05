"""
Authentication dependency for PDF viewing that supports both
Bearer tokens and temporary view tokens.
"""

from fastapi import Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from app.auth.cognito import get_optional_user
from app.auth.view_token import verify_view_token
from app.users.models import User


async def get_user_for_view(
    template_id: UUID = Path(...),
    token: Optional[str] = Query(None, description="Temporary view token"),
    current_user: Optional[User] = Depends(get_optional_user),
) -> Optional[str]:
    """
    Authenticate user for viewing a template.
    Accepts either Bearer token (via get_optional_user) or view token query param.

    Returns:
        user_id if authenticated, raises HTTPException otherwise
    """
    # Check view token first
    if token:
        user_id = verify_view_token(token, str(template_id))
        if user_id:
            return user_id
        raise HTTPException(status_code=401, detail="Invalid or expired view token")

    # Check regular authentication
    if current_user:
        return current_user.cognito_user_id

    # No valid authentication
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide either Bearer token or view token.",
    )
