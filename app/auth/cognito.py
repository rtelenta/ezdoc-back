from jose import jwt, JWTError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import requests
from functools import lru_cache
from typing import Dict

from app.db.session import get_db
from app.users.models import User
from app.users.repositories import get_or_create_user
from app.config import (
    COGNITO_REGION,
    COGNITO_USER_POOL_ID,
    COGNITO_APP_CLIENT_ID,
)

# HTTP Bearer security scheme
security = HTTPBearer()


@lru_cache()
def get_cognito_jwks() -> dict:
    """
    Fetch and cache Cognito's JSON Web Key Set (JWKS).
    These are the public keys used to verify JWT signatures.
    """
    jwks_url = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    response.raise_for_status()
    return response.json()


def verify_cognito_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    """
    Validates the JWT token from Cognito Authorization header.
    Returns the decoded token claims if valid.

    Raises HTTPException if token is invalid or expired.
    """
    token = credentials.credentials

    try:
        # Get the JWKS (public keys) from Cognito
        jwks = get_cognito_jwks()

        # Decode and verify the JWT token
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=COGNITO_APP_CLIENT_ID,
            issuer=f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}",
            options={"verify_exp": True},  # Verify token hasn't expired
        )

        return claims

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    claims: Dict = Depends(verify_cognito_token),
    db: Session = Depends(get_db),
) -> User:
    """
    Main authentication dependency.

    This function:
    1. Validates the JWT token (via verify_cognito_token dependency)
    2. Extracts user info from token claims
    3. Creates user in DB on first request (auto-registration)
    4. Updates last_login_at timestamp
    5. Returns the User object

    Usage in endpoints:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            # current_user is automatically validated and loaded from DB
            return {"user_id": current_user.cognito_user_id}
    """
    # Extract user information from JWT claims
    cognito_user_id = claims.get("sub")  # Unique Cognito user ID
    email = claims.get("email")
    name = claims.get("name")

    if not cognito_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required user information",
        )

    # Get or create user in database (automatic registration on first API call)
    user = get_or_create_user(
        db=db, cognito_user_id=cognito_user_id, email=email, name=name
    )

    return user


# Optional: Dependency for routes that don't require authentication but want user info if available
def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Returns current user if authenticated, None otherwise.
    Useful for endpoints that work both authenticated and unauthenticated.
    """
    if not credentials:
        return None

    try:
        claims = verify_cognito_token(credentials)
        cognito_user_id = claims.get("sub")
        email = claims.get("email")
        name = claims.get("name")

        if cognito_user_id and email:
            return get_or_create_user(
                db=db, cognito_user_id=cognito_user_id, email=email, name=name
            )
    except:
        pass

    return None
