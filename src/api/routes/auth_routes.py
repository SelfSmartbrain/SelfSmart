from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from src.api.auth import create_access_token, get_password_hash, verify_password, User
from src.api.dependencies import get_user_repo
from src.db.repositories.user_repo import UserRepository

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

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
    
    access_token = create_access_token(data={"sub": new_user.email}, expires_delta=timedelta(days=7))
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=User(id=new_user.id, email=new_user.email)
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
        
    access_token = create_access_token(data={"sub": user_db.email}, expires_delta=timedelta(days=7))
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=User(id=user_db.id, email=user_db.email)
    )
