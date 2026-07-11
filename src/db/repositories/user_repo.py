from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User
from src.db.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository for managing User entities."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, email: str, hashed_password: str) -> User:
        """Create a new user."""
        user = User(email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_api_key(self, api_key_hash: str) -> Optional[User]:
        """Get a user by their API key hash."""
        stmt = select(User).where(User.api_key_hash == api_key_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
