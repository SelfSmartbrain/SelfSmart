"""
Enhanced authentication with refresh tokens, token rotation, and revocation.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from enum import Enum

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.db.repositories.user_repo import UserRepository
from src.db.session import get_session
from src.db.models import User
from src.config.logging import get_logger

logger = get_logger(__name__)


class TokenType(Enum):
    """Token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # Subject (user ID)
    email: str
    type: TokenType
    jti: str  # JWT ID (unique token identifier)
    iat: datetime  # Issued at
    exp: datetime  # Expiration


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires


class TokenRefreshRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str


class User(BaseModel):
    """User model."""

    id: uuid.UUID
    email: str
    is_active: bool = True


class RefreshToken(BaseModel):
    """Refresh token model for database storage."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    token_jti: str
    token_hash: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[uuid.UUID] = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create an access token."""
    settings = get_settings()
    secret_key = settings.secret_key

    if settings.is_production and secret_key == "dev-secret-key-change-in-production":
        raise ValueError("SECRET_KEY must be configured with a secure value in production")

    to_encode = data.copy()

    # Add token type and JWT ID
    to_encode["type"] = TokenType.ACCESS.value
    to_encode["jti"] = str(uuid.uuid4())

    # Set expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode["iat"] = datetime.now(timezone.utc)
    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(
    user_id: uuid.UUID, email: str, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a refresh token."""
    settings = get_settings()
    secret_key = settings.secret_key

    to_encode = {
        "sub": str(user_id),
        "email": email,
        "type": TokenType.REFRESH.value,
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(timezone.utc).isoformat(),
    }

    # Set expiration (longer than access token)
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)

    to_encode["exp"] = expire.isoformat()

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


async def store_refresh_token(
    session: AsyncSession, user_id: uuid.UUID, token_jti: str, token_hash: str, expires_at: datetime
) -> RefreshToken:
    """Store refresh token in database."""
    refresh_token = RefreshToken(
        user_id=user_id,
        token_jti=token_jti,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    session.add(refresh_token)
    await session.commit()
    await session.refresh(refresh_token)

    return refresh_token


async def revoke_refresh_token(
    session: AsyncSession, token_jti: str, replaced_by: Optional[uuid.UUID] = None
) -> bool:
    """Revoke a refresh token."""
    result = await session.execute(select(RefreshToken).where(RefreshToken.token_jti == token_jti))
    token = result.scalar_one_or_none()

    if token:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        token.replaced_by = replaced_by
        await session.commit()
        return True

    return False


async def revoke_all_user_tokens(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Revoke all refresh tokens for a user."""
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
    )
    tokens = result.scalars().all()

    count = 0
    for token in tokens:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        count += 1

    await session.commit()
    return count


async def verify_refresh_token(session: AsyncSession, token: str) -> Optional[TokenPayload]:
    """Verify a refresh token and check if it's revoked."""
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

        # Check token type
        if payload.get("type") != TokenType.REFRESH.value:
            return None

        # Check if token is revoked
        token_jti = payload.get("jti")
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_jti == token_jti, RefreshToken.revoked == False
            )
        )
        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp:
            exp_datetime = datetime.fromisoformat(exp)
            if exp_datetime < datetime.now(timezone.utc):
                return None

        return TokenPayload(**payload)

    except JWTError:
        return None


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db_session=Depends(get_session),
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> User:
    """Get current user from access token or API key."""
    settings = get_settings()
    secret_key = settings.secret_key
    if settings.is_production and secret_key == "dev-secret-key-change-in-production":
        raise ValueError("SECRET_KEY must be configured with a secure value")
    repo = UserRepository(db_session)

    if not token and not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Try token authentication
    if token:
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])

            # Check token type
            if payload.get("type") != TokenType.ACCESS.value:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
                )

            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
                )

            user_db = await repo.get_by_email(email)

            if user_db is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
                )

            return User(id=user_db.id, email=user_db.email)

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

    # Try API key authentication
    if api_key:
        api_key_hash = get_password_hash(api_key)
        user_db = await repo.get_by_api_key(api_key_hash)

        if user_db is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        return User(id=user_db.id, email=user_db.email)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )
