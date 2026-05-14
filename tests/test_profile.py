import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import set_db_path, close_connection
from app.repositories.profile import ProfileRepository
from app.repositories.user import UserRepository
from app.services.profile import ProfileService
from app.models.profile import (
    ProfileBasic, WorkExperienceCreate, EducationCreate, CertificationCreate,
    SkillCreate, ProjectCreate, AchievementCreate, CourseCreate
)


@pytest.fixture(autouse=True)
async def setup_db():
    await close_connection()
    set_db_path(":memory:")
    yield
    await close_connection()


@pytest.fixture
def repo():
    return ProfileRepository()


@pytest.fixture
def user_repo():
    return UserRepository()


@pytest.fixture
async def service(repo, user_repo):
    await user_repo.initialize()
    return ProfileService(repo)


@pytest.mark.asyncio
async def test_profile_repository_basic_info(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    
    result = await repo.update_basic(user["id"], name="John Doe", title="Software Engineer", summary="Experienced dev", location="NYC", years_of_experience=5)
    
    assert result["name"] == "John Doe"
    assert result["title"] == "Software Engineer"
    assert result["summary"] == "Experienced dev"
    assert result["location"] == "NYC"
    assert result["years_of_experience"] == 5


@pytest.mark.asyncio
async def test_profile_repository_work_experience(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    result = await repo.create_work_experience(user_id, "Acme Corp", "Developer", "NYC", "2020-01", None, True, "Built stuff")
    
    assert result["company"] == "Acme Corp"
    assert result["title"] == "Developer"
    assert result["current"] == True
    
    all_exp = await repo.get_work_experience(user_id)
    assert len(all_exp) == 1
    
    updated = await repo.update_work_experience(result["id"], user_id, "Acme Corp", "Senior Dev", "NYC", "2020-01", "2023-12", False, "Built more stuff")
    assert updated["title"] == "Senior Dev"
    assert updated["current"] == False
    
    deleted = await repo.delete_work_experience(result["id"], user_id)
    assert deleted == True


@pytest.mark.asyncio
async def test_profile_repository_education(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    result = await repo.create_education(user_id, "MIT", "Bachelor of Science", "CS", "2015-09", "2019-06", 3.8)
    
    assert result["institution"] == "MIT"
    assert result["degree"] == "Bachelor of Science"
    assert result["gpa"] == 3.8
    
    all_edu = await repo.get_education(user_id)
    assert len(all_edu) == 1
    
    deleted = await repo.delete_education(result["id"], user_id)
    assert deleted == True


@pytest.mark.asyncio
async def test_profile_repository_certification(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    result = await repo.create_certification(user_id, "AWS Solutions Architect", "AWS", "2023-01", "2026-01", "ABC123", None)
    
    assert result["name"] == "AWS Solutions Architect"
    assert result["issuer"] == "AWS"
    assert result["credential_id"] == "ABC123"
    
    all_certs = await repo.get_certifications(user_id)
    assert len(all_certs) == 1
    
    deleted = await repo.delete_certification(result["id"], user_id)
    assert deleted == True


@pytest.mark.asyncio
async def test_profile_repository_skills(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    result = await repo.create_skill(user_id, "Python", "technical", 5, 3)
    
    assert result["name"] == "Python"
    assert result["category"] == "technical"
    assert result["proficiency"] == 5
    assert result["years_of_experience"] == 3
    
    all_skills = await repo.get_skills(user_id)
    assert len(all_skills) == 1
    
    deleted = await repo.delete_skill(result["id"], user_id)
    assert deleted == True


@pytest.mark.asyncio
async def test_profile_repository_projects(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    result = await repo.create_project(user_id, "My App", "Built an app", "Lead", ["React", "Node"], ["Shipped to 1M users"], "2022-01", "2022-12")
    
    assert result["name"] == "My App"
    assert result["role"] == "Lead"
    assert result["technologies"] == ["React", "Node"]
    assert result["outcomes"] == ["Shipped to 1M users"]
    
    all_projects = await repo.get_projects(user_id)
    assert len(all_projects) == 1
    
    deleted = await repo.delete_project(result["id"], user_id)
    assert deleted == True


@pytest.mark.asyncio
async def test_profile_repository_achievements(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    result = await repo.create_achievement(user_id, "Best Employee", "award", "Got recognition", "2023-06", "Acme Corp")
    
    assert result["title"] == "Best Employee"
    assert result["category"] == "award"
    assert result["organization"] == "Acme Corp"
    
    all_ach = await repo.get_achievements(user_id)
    assert len(all_ach) == 1
    
    deleted = await repo.delete_achievement(result["id"], user_id)
    assert deleted == True


@pytest.mark.asyncio
async def test_profile_repository_courses(repo, user_repo):
    await user_repo.initialize()
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    result = await repo.create_course(user_id, "ML Course", "Coursera", "2023-05", "https://cert.com", "Learned ML")
    
    assert result["name"] == "ML Course"
    assert result["provider"] == "Coursera"
    assert result["certificate_url"] == "https://cert.com"
    
    all_courses = await repo.get_courses(user_id)
    assert len(all_courses) == 1
    
    deleted = await repo.delete_course(result["id"], user_id)
    assert deleted == True


@pytest.mark.asyncio
async def test_profile_service_basic(service, user_repo):
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    basic = ProfileBasic(title="Engineer", summary="Summary", location="NYC", years_of_experience=3)
    result = await service.update_basic(user_id, basic)
    
    assert result["title"] == "Engineer"
    assert result["location"] == "NYC"


@pytest.mark.asyncio
async def test_profile_service_full_profile(service, user_repo):
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    basic = ProfileBasic(name="Test User", title="Engineer", summary="Summary", location="NYC", years_of_experience=3)
    await service.update_basic(user_id, basic)
    
    exp_data = WorkExperienceCreate(company="Acme", title="Dev", location="NYC", start_date="2020-01", end_date=None, current=True, description="Worked")
    await service.create_work_experience(user_id, exp_data)
    
    skill_data = SkillCreate(name="Python", category="technical", proficiency=5, years_of_experience=3)
    await service.create_skill(user_id, skill_data)
    
    edu_data = EducationCreate(institution="MIT", degree="BS", field="CS", start_date="2015", end_date="2019", gpa=3.8)
    await service.create_education(user_id, edu_data)
    
    cert_data = CertificationCreate(name="AWS", issuer="Amazon", issue_date="2023-01")
    await service.create_certification(user_id, cert_data)
    
    proj_data = ProjectCreate(name="App", description="Built it", role="Lead", technologies=["React"], outcomes=["Shipped"], start_date="2022", end_date="2023")
    await service.create_project(user_id, proj_data)
    
    ach_data = AchievementCreate(title="Award", category="award", description="Won", date="2023")
    await service.create_achievement(user_id, ach_data)
    
    course_data = CourseCreate(name="Course", provider="Coursera", completion_date="2023-06")
    await service.create_course(user_id, course_data)
    
    profile = await service.get_profile(user_id)
    
    assert profile.name == "Test User"
    assert profile.title == "Engineer"
    assert len(profile.work_experience) == 1
    assert profile.work_experience[0].company == "Acme"
    assert len(profile.skills) == 1
    assert profile.skills[0].name == "Python"
    assert len(profile.education) == 1
    assert profile.education[0].institution == "MIT"
    assert len(profile.certifications) == 1
    assert profile.certifications[0].name == "AWS"
    assert len(profile.projects) == 1
    assert profile.projects[0].name == "App"
    assert len(profile.achievements) == 1
    assert profile.achievements[0].title == "Award"
    assert len(profile.courses) == 1
    assert profile.courses[0].name == "Course"


@pytest.mark.asyncio
async def test_profile_service_update_delete(service, user_repo):
    user = await user_repo.create("testuser", "test@example.com")
    user_id = user["id"]
    
    skill_data = SkillCreate(name="Java", category="technical", proficiency=4, years_of_experience=2)
    created = await service.create_skill(user_id, skill_data)
    
    updated_data = SkillCreate(name="Java", category="technical", proficiency=5, years_of_experience=3)
    await service.update_skill(created.id, user_id, updated_data)
    
    skills = await service.get_skills(user_id)
    assert skills[0].proficiency == 5
    assert skills[0].years_of_experience == 3
    
    deleted = await service.delete_skill(created.id, user_id)
    assert deleted == True
    
    skills = await service.get_skills(user_id)
    assert len(skills) == 0


@pytest.mark.asyncio
async def test_profile_service_not_found(service, user_repo):
    user = await user_repo.create("testuser", "test@example.com")
    
    profile = await service.get_profile(999)
    assert profile is None
    
    basic = ProfileBasic(title="Test", summary="", location="", years_of_experience=0)
    result = await service.update_basic(999, basic)
    assert result is None