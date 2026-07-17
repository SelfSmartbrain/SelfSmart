"""Legacy auth dependencies for SelfSmart chat endpoints."""

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from src.utils.auth import TokenData, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token_data
