import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.repositories.user import UserRepository
from app.services.user import UserService
from app.models import User, ChatSession, Message


@pytest.mark.asyncio
async def test_user_repository_create():
    repo = UserRepository(":memory:")
    await repo.initialize()
    
    user = await repo.create("alice", "alice@example.com")
    assert user["name"] == "alice"
    assert user["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_user_service_create():
    repo = UserRepository(":memory:")
    await repo.initialize()
    service = UserService(repo)
    
    user = await service.create_user("bob", "bob@example.com")
    assert user.name == "bob"
    assert user.email == "bob@example.com"


@pytest.mark.asyncio
async def test_user_model_to_dict():
    user = User(id=1, name="test", email="test@test.com")
    d = user.to_dict()
    
    assert d["id"] == 1
    assert d["name"] == "test"
    assert d["email"] == "test@test.com"


@pytest.mark.asyncio
async def test_chat_session_model():
    session = ChatSession(id=1, user_id=1, title="Test Chat")
    d = session.to_dict()
    
    assert d["id"] == 1
    assert d["user_id"] == 1
    assert d["title"] == "Test Chat"


@pytest.mark.asyncio
async def test_message_model():
    msg = Message(id=1, session_id=1, role="user", content="Hello")
    d = msg.to_dict()
    
    assert d["id"] == 1
    assert d["session_id"] == 1
    assert d["role"] == "user"
    assert d["content"] == "Hello"