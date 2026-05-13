from typing import List
from app.models import Message
from app.repositories.message import MessageRepository

class MessageService:
    def __init__(self, repository: MessageRepository):
        self.repository = repository
        
    async def get_session_messages(self, session_id: int, limit: int = 100) -> List[Message]:
        rows = await self.repository.get_by_session(session_id, limit)
        return [Message(**row) for row in rows]
    
    async def add_user_message(self, session_id: int, content: str) -> Message:
        data = await self.repository.add(session_id, "user", content)
        return Message(**data)
    
    async def add_assistant_message(self, session_id: int, content: str) -> Message:
        data = await self.repository.add(session_id, "assistant", content)
        return Message(**data)