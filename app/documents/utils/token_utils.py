"""
Token generation and validation for document viewing.
These tokens are stored with the document and have longer expiration (24 hours).
"""

from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.config import SECRET_KEY

ALGORITHM = "HS256"


def create_document_token(
    document_id: Optional[str],
    template_id: str,
    user_id: str,
    expire_hours: int = 24,
) -> str:
    """
    Create a token for viewing a specific document.

    Args:
        document_id: The UUID of the document (optional, for future use)
        template_id: The UUID of the template used
        user_id: The cognito_user_id of the user creating the document
        expire_hours: Token expiration time in hours (default: 24)

    Returns:
        JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=expire_hours)

    payload = {
        "template_id": template_id,
        "user_id": user_id,
        "exp": expire,
        "type": "document_token",
    }

    if document_id:
        payload["document_id"] = document_id

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_document_token(token: str) -> Optional[dict]:
    """
    Verify a document token and return its payload if valid.

    Args:
        token: The JWT token to verify

    Returns:
        Token payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Verify token type
        if payload.get("type") != "document_token":
            return None

        return payload

    except JWTError:
        return None
