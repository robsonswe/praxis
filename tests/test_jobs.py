import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import set_db_path, close_connection
from app.repositories.job import JobRepository
from app.repositories.user import UserRepository
from app.services.job import JobService
from app.models.job import JobPostCreate


@pytest.fixture(autouse=True)
async def setup_db():
    await close_connection()
    set_db_path(":memory:")
    yield
    await close_connection()


@pytest.fixture
def job_repo():
    return JobRepository()


@pytest.fixture
def user_repo():
    return UserRepository()


@pytest.fixture
async def job_service(job_repo, user_repo):
    await user_repo.initialize()
    return JobService(job_repo)


@pytest.mark.asyncio
async def test_job_repository_create_list_delete(job_repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]

    result = await job_repo.create(
        user_id,
        "Product Designer",
        "Studio",
        "Remote",
        "full-time",
        "$80k-$110k",
        "https://example.com/job",
        "Design systems and tooling.",
        "Studio focused on global brand systems."
    )

    assert result["title"] == "Product Designer"
    assert result["company"] == "Studio"
    assert result["job_type"] == "full-time"
    assert result["company_description"] == "Studio focused on global brand systems."

    items = await job_repo.list_by_user(user_id)
    assert len(items) == 1
    assert items[0]["title"] == "Product Designer"

    deleted = await job_repo.delete(result["id"], user_id)
    assert deleted is True


@pytest.mark.asyncio
async def test_job_service_create_list(job_service, user_repo):
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]

    data = JobPostCreate(
        title="Data Analyst",
        company="Acme",
        location="NYC",
        job_type="contract",
        salary="$40/hr",
        link="https://example.com/role",
        description="Analyze metrics.",
        company_description="Retail operations and logistics team."
    )

    created = await job_service.create_job(user_id, data)
    assert created.title == "Data Analyst"
    assert created.job_type == "contract"
    assert created.company_description == "Retail operations and logistics team."

    items = await job_service.list_jobs(user_id)
    assert len(items) == 1
    assert items[0].company == "Acme"
