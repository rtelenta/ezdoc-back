from sqlalchemy.orm import Session
from app.users.models import User
from datetime import datetime
from typing import Optional


def get_user_by_cognito_id(db: Session, cognito_user_id: str) -> Optional[User]:
    """Get user by Cognito user ID"""
    return db.query(User).filter(User.cognito_user_id == cognito_user_id).first()


def get_or_create_user(
    db: Session, cognito_user_id: str, email: str, name: str = None
) -> User:
    """
    Get user from database or create if this is their first API request.
    This is called automatically on every authenticated request.
    """
    user = get_user_by_cognito_id(db, cognito_user_id)

    if not user:
        # First time this user makes an API request - create their profile
        print(f"🆕 Creating new user profile for {email}")
        user = User(
            cognito_user_id=cognito_user_id,
            email=email,
            full_name=name,
            created_at=datetime.utcnow(),
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update last login timestamp
        user.last_login_at = datetime.utcnow()
        db.commit()

    return user


def update_user_profile(
    db: Session,
    cognito_user_id: str,
    full_name: str = None,
) -> User:
    """Update user profile information"""
    user = get_user_by_cognito_id(db, cognito_user_id)

    if not user:
        raise ValueError("User not found")

    # Update provided fields
    if full_name is not None:
        user.full_name = full_name

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return user
