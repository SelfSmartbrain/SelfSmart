"""
Enhanced authentication routes with refresh token support.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.api.auth_enhanced import (
    get_current_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    store_refresh_token,
    revoke_refresh_token,
    verify_refresh_token,
    User as AuthUser,
    TokenPair,
    TokenRefreshRequest,
)
from src.api.dependencies import get_user_repo
from src.db.repositories.user_repo import UserRepository
from src.db.session import get_session
from src.db.models import User as UserModel

router = APIRouter()


class UserCreate(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str | None = None


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Register a new user."""
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate password strength
    if not _is_strong_password(user_data.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters with uppercase, lowercase, and numbers",
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = await user_repo.create_user(email=user_data.email, hashed_password=hashed_password)

    # Create tokens
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=timedelta(minutes=15)
    )
    refresh_token = create_refresh_token(
        user_id=new_user.id, email=new_user.email, expires_delta=timedelta(days=7)
    )

    # Store refresh token
    await store_refresh_token(
        session=session,
        user_id=new_user.id,
        token_jti=refresh_token.split(".")[1],  # Extract JTI from token
        token_hash=get_password_hash(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=900,  # 15 minutes
        user=AuthUser(id=new_user.id, email=new_user.email),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Login with email and password."""
    user_db = await user_repo.get_by_email(form_data.username)

    if not user_db or not verify_password(form_data.password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user_db.email}, expires_delta=timedelta(minutes=15)
    )
    refresh_token = create_refresh_token(
        user_id=user_db.id, email=user_db.email, expires_delta=timedelta(days=7)
    )

    # Store refresh token
    await store_refresh_token(
        session=session,
        user_id=user_db.id,
        token_jti=refresh_token.split(".")[1],
        token_hash=get_password_hash(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=900,
        user=AuthUser(id=user_db.id, email=user_db.email),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: TokenRefreshRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Refresh access token using refresh token."""
    # Verify refresh token
    token_payload = await verify_refresh_token(session, request.refresh_token)

    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

    # Get user
    user_db = await user_repo.get_by_email(token_payload.email)
    if not user_db:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Revoke old refresh token
    await revoke_refresh_token(session=session, token_jti=token_payload.jti, replaced_by=None)

    # Create new tokens
    access_token = create_access_token(
        data={"sub": user_db.email}, expires_delta=timedelta(minutes=15)
    )
    new_refresh_token = create_refresh_token(
        user_id=user_db.id, email=user_db.email, expires_delta=timedelta(days=7)
    )

    # Store new refresh token
    await store_refresh_token(
        session=session,
        user_id=user_db.id,
        token_jti=new_refresh_token.split(".")[1],
        token_hash=get_password_hash(new_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=900,
        user=AuthUser(id=user_db.id, email=user_db.email),
    )


@router.post("/logout")
async def logout(
    refresh_token: str,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Logout by revoking refresh token."""
    try:
        payload = jwt.decode(refresh_token, get_settings().secret_key, algorithms=["HS256"])
        token_jti = payload.get("jti")

        if token_jti:
            await revoke_refresh_token(session=session, token_jti=token_jti)

    except JWTError:
        pass  # Token was invalid anyway

    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Logout from all devices by revoking all refresh tokens."""
    from src.api.auth_enhanced import revoke_all_user_tokens

    count = await revoke_all_user_tokens(session, current_user.id)

    return {"message": f"Successfully logged out from {count} device(s)"}


def _is_strong_password(password: str) -> bool:
    """Check if password meets strength requirements."""
    if len(password) < 8:
        return False

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    return has_upper and has_lower and has_digit
