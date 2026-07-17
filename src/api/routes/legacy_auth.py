"""Legacy auth endpoints — JSON body login/register for the Next.js frontend."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.api.deps.legacy_auth import get_current_user
from src.api.rate_limit import limiter
from src.api.services import chat_runtime
from src.utils.auth import TokenData, create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


@router.post("/register")
@limiter.limit("3/minute")
async def register(user_data: UserCreate, request_obj: Request):
    existing_user = await chat_runtime.conversation_manager.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    user_id = await chat_runtime.conversation_manager.create_user(
        user_data.email, hashed_password, user_data.full_name
    )

    access_token = create_access_token(data={"sub": user_id, "email": user_data.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login")
@limiter.limit("5/minute")
async def login(credentials: UserLogin, request_obj: Request):
    user = await chat_runtime.conversation_manager.get_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user["id"], "email": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    return {"user_id": current_user.user_id, "email": current_user.email}
