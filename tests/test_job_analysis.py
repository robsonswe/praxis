import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from app.models.job import JobAnalysis, FitInsight
from app.repositories.job_analysis import JobAnalysisRepository
from app.repositories.job import JobRepository
from app.services.job_analysis import JobAnalysisService
from app.services.profile import ProfileService
from app.services.behavioral import BehavioralService
from app.services.ai_service import AIService
from app.models.profile import UserProfile
from app.models.behavioral import BehavioralProfile

@pytest.fixture
async def job_analysis_repo():
    from app.database import init_db
    await init_db()
    repo = JobAnalysisRepository()
    return repo

@pytest.fixture
async def mock_ai_service():
    service = MagicMock(spec=AIService)
    service.initialize = AsyncMock()
    service.get_user_settings = AsyncMock(return_value={"provider": "test", "model": "test-model"})
    return service

@pytest.fixture
async def mock_profile_service():
    service = MagicMock(spec=ProfileService)
    service.get_profile = AsyncMock(return_value=UserProfile(
        id=1, name="Test User", email="test@example.com", title="Dev",
        summary="Summary", location="Loc", years_of_experience=5,
        work_experience=[], education=[], certifications=[], courses=[],
        achievements=[], skills=[], projects=[]
    ))
    return service

@pytest.fixture
async def mock_behavioral_service():
    service = MagicMock(spec=BehavioralService)
    now = datetime.now()
    service.get_profile = AsyncMock(return_value=BehavioralProfile(
        user_id=1,
        core_traits=[],
        operating_styles=[],
        strategic_insights=[],
        created_at=now,
        updated_at=now
    ))
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
async def test_job_analysis_upsert_and_get(job_analysis_repo):
    analysis = JobAnalysis(
        job_id=1,
        user_id=1,
        overall_score=80,
        technical_fit=85,
        cultural_fit=75,
        strengths=[FitInsight(area="Python", description="Expert", severity="high", actionable=False)],
        gaps=[],
        red_flags=[],
        recommendations=["Practice more"],
        positioning_strategy="Be confident"
    )
    
    # Test Upsert
    saved = await job_analysis_repo.upsert(analysis)
    assert saved.overall_score == 80
    assert len(saved.strengths) == 1
    
    # Test Get
    fetched = await job_analysis_repo.get_by_job_user(1, 1)
    assert fetched.job_id == 1
    assert fetched.overall_score == 80
    assert fetched.positioning_strategy == "Be confident"

@pytest.mark.asyncio
async def test_job_analysis_service_success(mock_ai_service, mock_profile_service, mock_behavioral_service, mock_job_repo, job_analysis_repo):
    # Mock AI response
    mock_ai_service.send_message.return_value = {
        "content": json.dumps({
            "technical_fit": 90,
            "cultural_fit": 80,
            "strengths": [],
            "gaps": [],
            "red_flags": [],
            "recommendations": [],
            "positioning_strategy": "Pitch well"
        })
    }
    
    service = JobAnalysisService(
        job_analysis_repo, mock_job_repo, mock_profile_service, 
        mock_behavioral_service, mock_ai_service
    )
    
    result = await service.generate_analysis(1, 1)
    
    assert result.technical_fit == 90
    assert result.cultural_fit == 80
    assert result.overall_score == 85 # (90+80)/2
    assert result.positioning_strategy == "Pitch well"

@pytest.mark.asyncio
async def test_job_analysis_service_retry_logic(mock_ai_service, mock_profile_service, mock_behavioral_service, mock_job_repo, job_analysis_repo):
    # Mock AI response sequence: 2 failures, 1 success
    mock_ai_service.send_message.side_effect = [
        {"content": "invalid json"},
        {"content": "still bad"},
        {"content": json.dumps({
            "technical_fit": 70,
            "cultural_fit": 70,
            "strengths": [], "gaps": [], "red_flags": [], "recommendations": [],
            "positioning_strategy": "Final"
        })}
    ]
    
    service = JobAnalysisService(
        job_analysis_repo, mock_job_repo, mock_profile_service, 
        mock_behavioral_service, mock_ai_service
    )
    
    result = await service.generate_analysis(1, 1)
    assert result.overall_score == 70
    assert mock_ai_service.send_message.call_count == 3

@pytest.mark.asyncio
async def test_job_analysis_service_hard_failure(mock_ai_service, mock_profile_service, mock_behavioral_service, mock_job_repo, job_analysis_repo):
    # Mock AI response: Always invalid
    mock_ai_service.send_message.return_value = {"content": "not json"}
    
    service = JobAnalysisService(
        job_analysis_repo, mock_job_repo, mock_profile_service, 
        mock_behavioral_service, mock_ai_service
    )
    
    with pytest.raises(Exception) as excinfo:
        await service.generate_analysis(1, 1)
    
    assert "AI failed to provide a valid analysis after 3 attempts" in str(excinfo.value)
    assert mock_ai_service.send_message.call_count == 3

@pytest.mark.asyncio
async def test_job_analysis_service_provider_error(mock_ai_service, mock_profile_service, mock_behavioral_service, mock_job_repo, job_analysis_repo):
    # Mock AI response: Provider error (like rate limit)
    mock_ai_service.send_message.return_value = {"error": "Rate limit exceeded"}
    
    service = JobAnalysisService(
        job_analysis_repo, mock_job_repo, mock_profile_service, 
        mock_behavioral_service, mock_ai_service
    )
    
    with pytest.raises(Exception) as excinfo:
        await service.generate_analysis(1, 1)
    
    assert "Failed to communicate with AI provider: Rate limit exceeded" in str(excinfo.value)
    assert mock_ai_service.send_message.call_count == 1 # Should not retry provider errors
