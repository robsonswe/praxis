from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    created_at: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at
        }


@dataclass
class ChatSession:
    id: Optional[int] = None
    user_id: int = 0
    title: str = ""
    created_at: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at
        }


@dataclass
class Message:
    id: Optional[int] = None
    session_id: int = 0
    role: str = "user"  # "user" or "assistant"
    content: str = ""
    created_at: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at
        }