import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import User, ChatSession, Message


def test_user_model():
    user = User(id=1, username="alice", email="alice@test.com")
    d = user.to_dict()
    assert d["username"] == "alice"
    assert d["email"] == "alice@test.com"


def test_chat_session_model():
    session = ChatSession(id=1, user_id=1, title="My Chat")
    d = session.to_dict()
    assert d["title"] == "My Chat"


def test_message_model_user_role():
    msg = Message(id=1, session_id=1, role="user", content="Hello!")
    d = msg.to_dict()
    assert d["role"] == "user"


def test_message_model_assistant_role():
    msg = Message(session_id=1, role="assistant", content="Hi there!")
    d = msg.to_dict()
    assert d["role"] == "assistant"