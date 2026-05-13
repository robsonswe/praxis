from app.models import User
from app.repositories.user import UserRepository

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository
        
    async def create_user(self, username: str, email: str) -> User:
        data = await self.repository.create(username, email)
        return User(**data)
    
    async def get_user(self, user_id: int) -> User | None:
        data = await self.repository.get_by_id(user_id)
        if data:
            return User(**data)
        return None
    
    async def get_by_username(self, username: str) -> User | None:
        data = await self.repository.get_by_username(username)
        if data:
            return User(**data)
        return None

    async def get_by_email(self, email: str) -> User | None:
        data = await self.repository.get_by_email(email)
        if data:
            return User(**data)
        return None