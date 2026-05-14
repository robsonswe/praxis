from app.models import User
from app.repositories.user import UserRepository

class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository
        
    async def create_user(self, name: str, email: str) -> User:
        data = await self.repository.create(name, email)
        return User(**data)
    
    async def get_user(self, user_id: int) -> User | None:
        data = await self.repository.get_by_id(user_id)
        if data:
            return User(**data)
        return None
    
    async def get_by_name(self, name: str) -> User | None:
        data = await self.repository.get_by_name(name)
        if data:
            return User(**data)
        return None

    async def get_by_email(self, email: str) -> User | None:
        data = await self.repository.get_by_email(email)
        if data:
            return User(**data)
        return None