from typing import List
from app.models import ChatSession, Message
from app.repositories.chat_session import ChatSessionRepository

class ChatSessionService:
    def __init__(self, repository: ChatSessionRepository):
        self.repository = repository
        
    async def create_session(self, user_id: int, title: str) -> ChatSession:
        data = await self.repository.create(user_id, title)
        return ChatSession(**data)
    
    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        rows = await self.repository.get_by_user(user_id)
        return [ChatSession(**row) for row in rows]
    
    async def get_session(self, session_id: int) -> ChatSession | None:
        data = await self.repository.get_by_id(session_id)
        if data:
            return ChatSession(**data)
        return None
    
    async def delete_session(self, session_id: int):
        await self.repository.delete(session_id)

    async def update_session_title(self, session_id: int, title: str):
        await self.repository.update_title(session_id, title)