"""
Temporary token generation and validation for viewing templates.
These tokens are short-lived and scoped to specific template IDs.
"""

from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.config import SECRET_KEY

# Token settings
VIEW_TOKEN_EXPIRE_MINUTES = 15
ALGORITHM = "HS256"


def create_view_token(template_id: str, user_id: str) -> str:
    """
    Create a temporary token for viewing a specific template.

    Args:
        template_id: The UUID of the template
        user_id: The cognito_user_id of the user requesting access

    Returns:
        JWT token string valid for VIEW_TOKEN_EXPIRE_MINUTES
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=VIEW_TOKEN_EXPIRE_MINUTES)

    payload = {
        "template_id": template_id,
        "user_id": user_id,
        "exp": expire,
        "type": "view_token",
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_view_token(token: str, template_id: str) -> Optional[str]:
    """
    Verify a view token and return the user_id if valid.

    Args:
        token: The JWT token to verify
        template_id: The template ID being accessed (must match token)

    Returns:
        user_id if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != "view_token":
            return None

        # Verify template_id matches
        if payload.get("template_id") != template_id:
            return None

        # Token is valid, return user_id
        return payload.get("user_id")

    except JWTError:
        return None
