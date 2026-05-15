import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.repositories.mock_interview import MockInterviewRepository
from app.repositories.job import JobRepository
from app.services.mock_interview import MockInterviewService
from app.services.ai_service import AIService

@pytest.fixture
async def mock_repo():
    from app.database import init_db, get_connection
    await init_db()
    
    # Create required user and job to satisfy foreign key constraints
    conn = await get_connection()
    await conn.execute("INSERT INTO users (id, name, email) VALUES (1, 'Test User', 'test@test.com')")
    await conn.execute("INSERT INTO jobs (id, user_id, title, company) VALUES (1, 1, 'Dev', 'Corp')")
    await conn.commit()
    
    return MockInterviewRepository()

@pytest.fixture
async def mock_ai_service():
    service = MagicMock(spec=AIService)
    service.initialize = AsyncMock()
    return service

@pytest.fixture
async def mock_job_repo():
    service = MagicMock(spec=JobRepository)
    service.get_by_id = AsyncMock(return_value={
        "id": 1, "user_id": 1, "title": "Software Engineer", "company": "Tech Corp",
        "description": "Reqs...", "company_description": "Culture..."
    })
    return service

@pytest.mark.asyncio
async def test_repository_create_and_get_session(mock_repo):
    questions = [{"index": 0, "text": "Q1"}]
    session = await mock_repo.create_session(
        user_id=1, job_id=1, interview_type="behavioral",
        response_mode="text", time_per_question=180, language="en",
        introduction_message="Hello",
        questions=questions, inferred_level="mid"
    )
    assert session["id"] > 0
    assert session["status"] == "in_progress"

    fetched = await mock_repo.get_session(session["id"], 1)
    assert fetched["id"] == session["id"]
    assert len(fetched["questions"]) == 1
    assert fetched["questions"][0]["text"] == "Q1"

@pytest.mark.asyncio
async def test_repository_save_answer(mock_repo):
    session = await mock_repo.create_session(
        user_id=1, job_id=1, interview_type="behavioral",
        response_mode="text", time_per_question=180, language="en",
        introduction_message="Hello",
        questions=[{"index": 0, "text": "Q1"}], inferred_level="mid"
    )
    
    await mock_repo.save_answer(
        session_id=session["id"], question_index=0, question_text="Q1",
        question_type="behavioral", dimension="Dim", metric="Metric",
        user_answer="My answer", ai_evaluation={"score": 8}, score=8,
        time_taken=60, has_follow_up=False
    )
    
    answers = await mock_repo.get_answers(session["id"])
    assert len(answers) == 1
    assert answers[0]["score"] == 8
    assert answers[0]["user_answer"] == "My answer"

@pytest.fixture
async def mock_profile_service():
    service = MagicMock()
    service.get_profile = AsyncMock(return_value=None)
    return service

@pytest.mark.asyncio
async def test_service_start_session(mock_repo, mock_job_repo, mock_ai_service, mock_profile_service):
    # Mock AI response for generate_questions
    mock_ai_service.send_message.return_value = {
        "content": json.dumps({
            "inferred_level": "senior",
            "introduction_message": "Hello!",
            "warm_up_question": {"type": "behavioral", "dimension": "Intro", "metric": "Warm-up", "text": "Q1", "evaluation_criteria": "E1"},
            "background_question": {"type": "behavioral", "dimension": "Bg", "metric": "Exp", "text": "Q2", "evaluation_criteria": "E2"},
            "core_questions": [
                {"type": "behavioral", "dimension_id": (i // 2) + 1, "metric_id": i + 1, "dimension": "D", "metric": "M", "text": f"Q{i+3}", "evaluation_criteria": f"E{i+3}"}
                for i in range(12)
            ],
            "closing_question": {"type": "behavioral", "dimension": "Close", "metric": "Close", "text": "Q15", "evaluation_criteria": "E15"}
        })
    }
    
    service = MockInterviewService(mock_repo, mock_job_repo, mock_profile_service, mock_ai_service)
    
    session = await service.start_session(1, {
        "job_id": 1,
        "interview_type": "behavioral",
        "response_mode": "text",
        "time_per_question": 180
    })
    
    assert session["id"] > 0
    assert len(session["questions"]) == 15
    assert session["inferred_level"] == "senior"

@pytest.mark.asyncio
async def test_service_evaluate_answer(mock_repo, mock_job_repo, mock_ai_service, mock_profile_service):
    service = MockInterviewService(mock_repo, mock_job_repo, mock_profile_service, mock_ai_service)
    
    # Pre-create a session
    session = await mock_repo.create_session(
        user_id=1, job_id=1, interview_type="behavioral",
        response_mode="text", time_per_question=180, language="en",
        introduction_message="Hello",
        questions=[{"index": 0, "type": "behavioral", "dimension": "D", "metric": "M", "text": "Q1", "evaluation_criteria": "E1"}], 
        inferred_level="mid"
    )
    
    # Mock AI evaluation
    mock_ai_service.send_message.return_value = {
        "content": json.dumps({
            "score": 8,
            "evaluation": "Good",
            "strengths": ["S1"],
            "improvements": ["I1"],
            "needs_follow_up": False,
            "follow_up_question": None
        })
    }
    
    evaluation = await service.evaluate_answer(1, session["id"], 0, "My answer", 60)
    
    assert evaluation["score"] == 8
    assert evaluation["needs_follow_up"] is False
    
    # Check if saved
    answers = await mock_repo.get_answers(session["id"])
    assert len(answers) == 1
    assert answers[0]["score"] == 8

@pytest.mark.asyncio
async def test_service_finish_session(mock_repo, mock_job_repo, mock_ai_service, mock_profile_service):
    service = MockInterviewService(mock_repo, mock_job_repo, mock_profile_service, mock_ai_service)
    
    session = await mock_repo.create_session(
        user_id=1, job_id=1, interview_type="behavioral",
        response_mode="text", time_per_question=180, language="en",
        introduction_message="Hello",
        questions=[], inferred_level="mid"
    )
    
    mock_ai_service.send_message.return_value = {
        "content": json.dumps({
            "overall_score": 85,
            "executive_summary": "Summary",
            "strongest_dimensions": ["D1"],
            "weakest_dimensions": ["D2"],
            "key_recommendations": ["R1"]
        })
    }
    
    result = await service.finish_session(1, session["id"])
    
    assert result["overall_score"] == 85
    assert result["summary"]["executive_summary"] == "Summary"
    
    # Verify DB update
    fetched = await mock_repo.get_session(session["id"], 1)
    assert fetched["status"] == "completed"
    assert fetched["overall_score"] == 85
