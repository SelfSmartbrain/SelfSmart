from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets

from src.config.settings import get_settings
from src.api.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
    User,
)
from src.api.dependencies import get_user_repo
from src.db.repositories.user_repo import UserRepository

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: User


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: str
    email: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    def new_password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    new_user = await user_repo.create_user(email=user_data.email, hashed_password=hashed_password)

    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=timedelta(minutes=15)
    )
    refresh_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=timedelta(days=7)
    )

    # Store the hash of the refresh token
    hashed_refresh_token = get_password_hash(refresh_token)
    await user_repo.update_refresh_token(
        user_id=new_user.id, refresh_token_hash=hashed_refresh_token
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=User(id=new_user.id, email=new_user.email),
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    user_db = await user_repo.get_by_email(form_data.username)
    if not user_db or not verify_password(form_data.password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user_db.email}, expires_delta=timedelta(minutes=15)
    )
    refresh_token = create_access_token(
        data={"sub": user_db.email}, expires_delta=timedelta(days=7)
    )

    # Store the hash of the refresh token
    hashed_refresh_token = get_password_hash(refresh_token)
    await user_repo.update_refresh_token(
        user_id=user_db.id, refresh_token_hash=hashed_refresh_token
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=User(id=user_db.id, email=user_db.email),
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
):
    settings = get_settings()
    # Verify the refresh token
    try:
        payload = jwt.decode(request.refresh_token, settings.secret_key, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Get the user
    user_db = await user_repo.get_by_email(email)
    if user_db is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Verify the refresh token hash
    if not user_db.refresh_token_hash or not verify_password(
        request.refresh_token, user_db.refresh_token_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Generate new access and refresh tokens
    new_access_token = create_access_token(
        data={"sub": user_db.email}, expires_delta=timedelta(minutes=15)
    )
    new_refresh_token = create_access_token(
        data={"sub": user_db.email}, expires_delta=timedelta(days=7)
    )

    # Update the stored refresh token hash (rotate refresh token)
    new_hashed_refresh_token = get_password_hash(new_refresh_token)
    await user_repo.update_refresh_token(
        user_id=user_db.id, refresh_token_hash=new_hashed_refresh_token
    )

    return TokenResponse(access_token=new_access_token, token_type="bearer")


@router.post("/logout")
async def logout(
    request: Request,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    current_user: User = Depends(get_current_user),
):
    # Clear the refresh token hash
    await user_repo.update_refresh_token(user_id=current_user.id, refresh_token_hash=None)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id), email=current_user.email, is_active=current_user.is_active
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    current_user: User = Depends(get_current_user),
):
    # Verify the current password
    user_db = await user_repo.get_by_email(current_user.email)
    if not user_db or not verify_password(request.current_password, user_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    # Update the password
    new_hashed_password = get_password_hash(request.new_password)
    await user_repo.update_password(user_id=user_db.id, hashed_password=new_hashed_password)

    return {"message": "Password updated successfully"}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    background_tasks: BackgroundTasks,
):
    # In a real application, we would send an email with a reset token.
    # For now, we'll just return a success message and log the email.
    user_db = await user_repo.get_by_email(request.email)
    if user_db:
        # Generate a reset token (in a real app, we would store this and send via email)
        reset_token = secrets.token_urlsafe(32)
        # Here we would typically store the hash of the reset token in the user record
        # and send an email with a link containing the token.
        # For demonstration, we'll just log it.
        print(f"Password reset token for {request.email}: {reset_token}")
    # Always return the same message to prevent user enumeration
    return {"message": "If the email is registered, a password reset link has been sent"}
