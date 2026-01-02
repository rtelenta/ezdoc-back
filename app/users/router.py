from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.cognito import get_current_user
from app.users.models import User
from app.users import schemas as user_schemas
from app.users import repositories as user_repositories

router = APIRouter()
PREFIX = "/users"


@router.get("/me", response_model=user_schemas.UserProfile)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    User is automatically created in DB on first API request.
    """
    return current_user


@router.patch("/me", response_model=user_schemas.UserProfile)
def update_my_profile(
    profile_update: user_schemas.UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile information"""
    return user_repositories.update_user_profile(
        db=db,
        cognito_user_id=current_user.cognito_user_id,
        full_name=profile_update.full_name,
    )
