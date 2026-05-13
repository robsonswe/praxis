import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.repositories.user import UserRepository
from app.repositories.chat_session import ChatSessionRepository
from app.repositories.message import MessageRepository


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_multiple_repositories_use_same_connection():
    """Test that multiple repository operations don't break each other"""
    # Create user first
    user_repo = UserRepository(":memory:")
    await user_repo.initialize()
    user = await user_repo.create("alice", "alice@test.com")
    
    # Create session - should not break after user creation
    session_repo = ChatSessionRepository(":memory:")
    await session_repo.initialize()
    session = await session_repo.create(user["id"], "Test Chat")
    
    # Create message - should work
    msg_repo = MessageRepository(":memory:")
    await msg_repo.initialize()
    msg = await msg_repo.add(session["id"], "user", "Hello")
    
    assert user["username"] == "alice"
    assert session["title"] == "Test Chat"
    assert msg["content"] == "Hello"


def test_json_response_format():
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"key": "value"})
    assert b'"key"' in response.body


def test_setup_page(client):
    response = client.get("/setup")
    assert response.status_code == 200