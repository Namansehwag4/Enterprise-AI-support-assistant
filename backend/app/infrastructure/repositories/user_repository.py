import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.interfaces.repositories import IUserRepository
from app.domain.models.user import UserInDB, UserCreate
from app.infrastructure.db.models import User

class UserRepository(IUserRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserInDB]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user_db = result.scalar_one_or_none()
        if user_db:
            return UserInDB.model_validate(user_db)
        return None

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        result = await self.db.execute(select(User).where(User.email == email))
        user_db = result.scalar_one_or_none()
        if user_db:
            return UserInDB.model_validate(user_db)
        return None

    async def create(self, user: UserCreate, hashed_password: str) -> UserInDB:
        user_db = User(
            email=user.email,
            password_hash=hashed_password,
            full_name=user.full_name,
            role=user.role.value
        )
        self.db.add(user_db)
        await self.db.commit()
        await self.db.refresh(user_db)
        return UserInDB.model_validate(user_db)
