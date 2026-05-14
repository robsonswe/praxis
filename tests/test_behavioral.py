import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Ensure app is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.services.behavioral import BehavioralService
from app.models.behavioral import BehavioralResponse
from app.repositories.user import UserRepository
from app.database import set_db_path, close_connection, get_connection, init_db

@pytest.fixture(autouse=True)
async def setup_db():
    await close_connection()
    set_db_path(":memory:")
    await init_db()
    yield
    await close_connection()

@pytest.fixture
def client():
    # Use follow_redirects=False to inspect 303s
    return TestClient(app)

@pytest.fixture
async def user_repo():
    repo = UserRepository()
    await repo.initialize()
    return repo

@pytest.fixture
def service():
    return BehavioralService()

@pytest.mark.asyncio
async def test_weighted_scoring_and_patterns(service, user_repo):
    """Test that the weighted matrix correctly calculates scores and triggers archetypes."""
    user = await user_repo.create("Logic Tester", "logic@example.com")
    user_id = user["id"]
    
    # Scenario: User picks all 'D' (Autonomous / Direct)
    # Expected Trait Scores:
    # Execution: D=1.0 -> 100%
    # Analytical: D=0.5 -> 50%
    # Collaboration: D=0.0 -> 0%
    # Resilience: D=0.75 -> 75%
    # Accountability: D=1.0 -> 100%
    
    responses = [BehavioralResponse(question_id=i, selected_option="D") for i in range(1, 26)]
    profile = await service.save_responses(user_id, responses)
    
    trait_scores = {t.name: t.score for t in profile.core_traits}
    assert trait_scores["Execution & Autonomy"] == 100.0
    assert trait_scores["Analytical Rigor & Quality"] == 50.0
    assert trait_scores["Collaboration & Synergy"] == 0.0
    assert trait_scores["Resilience & Pressure Handling"] == 75.0
    assert trait_scores["Accountability & Ownership"] == 100.0
    
    # Check Archetype detection
    # Dominant D + Accountability >= 70 -> "The Sentinel"
    insight_titles = [i.title for i in profile.strategic_insights]
    assert "The Sentinel" in insight_titles
    
    # Check Growth Alert
    # Collaboration is 0% < 40% -> "Collaboration Gap"
    assert "Collaboration Gap" in insight_titles
    
    # Check Strength Combo
    # Top 2 are Execution (100) and Accountability (100)
    # Execution + Accountability -> "Reliable Owner"
    assert "Reliable Owner" in insight_titles

@pytest.mark.asyncio
async def test_six_month_rule_controller(client, user_repo):
    """Test that the behavioral controller enforces the 6-month retake rule."""
    await user_repo.initialize()
    user = await user_repo.create("Rule User", "rule@example.com")
    user_id = user["id"]
    
    # 1. First submission should succeed (redirects to /profile)
    responses_data = {f"q_{i}": "A" for i in range(1, 26)}
    response = client.post(
        "/behavioral/submit", 
        data=responses_data, 
        cookies={"user_id": str(user_id)},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "/profile" in response.headers["location"]
    
    # 2. Second submission immediately after should be blocked
    response = client.post(
        "/behavioral/submit", 
        data=responses_data, 
        cookies={"user_id": str(user_id)},
        follow_redirects=False
    )
    # Still redirects to /profile but doesn't process (the check is before processing)
    assert response.status_code == 303
    
    # 3. Verify GET /behavioral also redirects if within 6 months
    # Note: Need to make sure the user has a profile in the DB for the GET check
    response = client.get(
        "/behavioral/", 
        cookies={"user_id": str(user_id)},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "/profile" in response.headers["location"]
    
    # 4. Simulate 7 months passing
    conn = await get_connection()
    seven_months_ago = (datetime.now() - timedelta(days=210)).isoformat()
    await conn.execute("UPDATE behavioral_profile SET updated_at = ? WHERE user_id = ?", (seven_months_ago, user_id))
    await conn.commit()
    
    # 5. GET /behavioral should now be accessible (200 OK)
    response = client.get(
        "/behavioral/", 
        cookies={"user_id": str(user_id)},
        follow_redirects=False
    )
    assert response.status_code == 200
    
    # 6. POST /behavioral/submit should now succeed again
    response = client.post(
        "/behavioral/submit", 
        data=responses_data, 
        cookies={"user_id": str(user_id)},
        follow_redirects=False
    )
    assert response.status_code == 303
    
    # 7. Verify the date was updated to today
    async with conn.execute("SELECT updated_at FROM behavioral_profile WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        updated_at = datetime.fromisoformat(row[0])
        assert (datetime.now() - updated_at).days < 1

@pytest.mark.asyncio
async def test_archetype_accelerator_pattern(service, user_repo):
    """Test detection of 'The Accelerator' archetype with 'C' pattern."""
    user = await user_repo.create("Agile Dev", "agile@example.com")
    user_id = user["id"]
    
    # Vector C (Agile) for all
    responses = [BehavioralResponse(question_id=i, selected_option="C") for i in range(1, 26)]
    profile = await service.save_responses(user_id, responses)
    
    # Trait scores check for C:
    # Execution: C=0.75 -> 75%
    # Analytical: C=0.0 -> 0%
    # Resilience: C=1.0 -> 100%
    
    insight_titles = [i.title for i in profile.strategic_insights]
    # Dominant C + Execution >= 70 -> "The Accelerator"
    assert "The Accelerator" in insight_titles
    assert "Rigor Gap" in insight_titles # Analytical is 0%
