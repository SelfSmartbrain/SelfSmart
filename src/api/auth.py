import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.config.settings import get_settings
from src.db.repositories.user_repo import UserRepository
from src.db.session import get_session

class User(BaseModel):
    id: uuid.UUID
    email: str
    is_active: bool = True

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    secret_key = settings.jwt_secret_key.get_secret_value()
    if not secret_key or secret_key == "dev-secret-change-in-production":
        raise ValueError("JWT_SECRET must be configured with a secure value in production")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt

async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db_session=Depends(get_session),
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> User:
    settings = get_settings()
    secret_key = settings.jwt_secret_key.get_secret_value()
    if not secret_key or secret_key == "dev-secret-change-in-production":
        raise ValueError("JWT_SECRET must be configured with a secure value")
    repo = UserRepository(db_session)

    if not token and not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token:
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        user_db = await repo.get_by_email(email)
        if user_db is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return User(id=user_db.id, email=user_db.email)
    
    # API Key authentication
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
