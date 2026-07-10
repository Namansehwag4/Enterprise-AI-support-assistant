from datetime import timedelta
from typing import Optional
from app.core.exceptions import EntityAlreadyExistsError, AuthenticationError
from app.core.security import get_password_hash, verify_password, create_access_token
from app.domain.interfaces.repositories import IUserRepository
from app.domain.models.user import UserCreate, UserResponse, UserInDB, Token

class AuthService:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    async def register_user(self, user: UserCreate) -> UserResponse:
        existing = await self.user_repo.get_by_email(user.email)
        if existing:
            raise EntityAlreadyExistsError(f"User with email {user.email} already exists")
            
        hashed_password = get_password_hash(user.password)
        created_user = await self.user_repo.create(user, hashed_password)
        return UserResponse(
            id=created_user.id,
            email=created_user.email,
            full_name=created_user.full_name,
            role=created_user.role,
            created_at=created_user.created_at
        )

    async def authenticate_user(self, email: str, password: str) -> UserInDB:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Incorrect email or password")
            
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Incorrect email or password")
            
        return user

    async def create_user_token(self, user: UserInDB) -> Token:
        access_token = create_access_token(subject=user.id)
        return Token(
            access_token=access_token,
            token_type="bearer"
        )
