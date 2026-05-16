import json as json_module
from pathlib import Path
from datetime import date, datetime
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.services.user import UserService
from app.repositories.user import UserRepository
from app.repositories.profile import ProfileRepository
from app.services.profile import ProfileService
from app.repositories.job import JobRepository
from app.services.job import JobService
from app.services.behavioral import BehavioralService
from app.repositories.job_analysis import JobAnalysisRepository
from app.services.job_analysis import JobAnalysisService
from app.repositories.mock_interview import MockInterviewRepository
from app.services.mock_interview import MockInterviewService
from app.repositories.chat_session import ChatSessionRepository
from app.services.chat_session import ChatSessionService
from app.services.ai_service import AIService
from app.models.profile import (
    ProfileBasic, WorkExperienceCreate, EducationCreate, CertificationCreate,
    CourseCreate, AchievementCreate, SkillCreate, ProjectCreate, UserProfile
)
from app.models.job import JobPostCreate
from app.database import init_db, get_connection, close_connection

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(['html', 'xml'])
)

# Load languages resource
LANGUAGES_PATH = BASE_DIR / "resources" / "languages.json"
LANGUAGES = []
try:
    LANGUAGES = json_module.loads(LANGUAGES_PATH.read_text(encoding="utf-8"))
except Exception:
    LANGUAGES = [{"code": "en", "name": "English"}]

user_repo = UserRepository()
user_service = UserService(user_repo)

profile_repo = ProfileRepository()
profile_service = ProfileService(profile_repo)

job_repo = JobRepository()
job_service = JobService(job_repo)
behavioral_service = BehavioralService()
ai_service = AIService()
job_analysis_repo = JobAnalysisRepository()
job_analysis_service = JobAnalysisService(
    job_analysis_repo,
    job_repo,
    profile_service,
    behavioral_service,
    ai_service
)
mock_repo = MockInterviewRepository()
mock_service = MockInterviewService(
    mock_repo,
    job_repo,
    profile_service,
    ai_service
)
chat_repo = ChatSessionRepository()
chat_service = ChatSessionService(chat_repo)



@router.get("/setup")
async def setup_page():
    template = env.get_template("setup.html")
    return HTMLResponse(content=template.render())


@router.post("/setup")
async def create_profile(name: str = Form(), email: str = Form()):
    await user_repo.initialize()
    
    # Check if email exists
    existing = await user_service.get_by_email(email)
    if existing:
        template = env.get_template("setup.html")
        return HTMLResponse(content=template.render(error="Email already registered"))
        
    user = await user_service.create_user(name, email)
    
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("user_id", str(user.id), httponly=True)
    return response


@router.get("/login")
async def login_page():
    template = env.get_template("login.html")
    return HTMLResponse(content=template.render())


@router.post("/login")
async def login(email: str = Form()):
    await user_repo.initialize()
    user = await user_service.get_by_email(email)
    
    if not user:
        template = env.get_template("login.html")
        return HTMLResponse(content=template.render(error="Email not found"))
        
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("user_id", str(user.id), httponly=True)
    return response


def get_current_user(request: Request) -> int | None:
    user_id = request.cookies.get("user_id")
    if user_id:
        return int(user_id)
    return None


def calculate_age(date_of_birth: str | None) -> int | None:
    if not date_of_birth:
        return None
    try:
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except ValueError:
        try:
            dob = datetime.fromisoformat(date_of_birth).date()
        except ValueError:
            return None
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 0:
        return None
    return age


def calculate_profile_completeness(profile: UserProfile) -> int:
    checks = [
        bool(profile.title),
        bool(profile.summary),
        bool(profile.location),
        bool(profile.date_of_birth),
        bool(profile.phone),
        bool(profile.website),
        bool(profile.linkedin),
        bool(profile.github),
        bool(profile.work_experience),
        bool(profile.education),
        bool(profile.skills),
        bool(profile.projects),
        bool(profile.certifications),
        bool(profile.achievements),
        bool(profile.courses)
    ]
    total = len(checks)
    if total == 0:
        return 0
    return int(round((sum(checks) / total) * 100))


@router.get("/")
async def root(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/login")
    
    profile = await profile_service.get_profile(user_id)
    if not profile:
        profile = UserProfile(
            id=user.id or 0,
            name=user.name,
            email=user.email,
            title=user.title or "",
            summary="",
            location="",
            years_of_experience=0,
            date_of_birth=user.date_of_birth,
            phone=user.phone,
            website=user.website,
            linkedin=user.linkedin,
            github=user.github,
            work_experience=[],
            education=[],
            certifications=[],
            courses=[],
            achievements=[],
            skills=[],
            projects=[]
        )

    profile_completeness = calculate_profile_completeness(profile)
    if profile_completeness >= 80:
        status_badge = "Healthy"
        profile_status = "Complete"
    elif profile_completeness >= 50:
        status_badge = "In Progress"
        profile_status = "Partial"
    else:
        status_badge = "Needs Work"
        profile_status = "Incomplete"

    # Calculate metrics
    jobs = await job_repo.list_by_user(user_id)
    interviews = await mock_service.list_sessions(user_id)
    chats = await chat_service.get_user_sessions(user_id)
    
    template = env.get_template("index.html")
    return HTMLResponse(content=template.render(
        user_name=profile.name,
        user_email=profile.email,
        active_page="dashboard",
        page_title="Dashboard",
        page_subtitle="Your career preparation overview",
        profile_completeness=profile_completeness,
        status_badge=status_badge,
        profile_status=profile_status,
        ai_status="Available",
        interview_status="Not Started",
        application_count=len(jobs),
        interview_count=len(interviews),
        chat_count=len(chats)
    ))


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.set_cookie("user_id", "", expires=0)
    return response


@router.get("/jobs")
async def jobs_page(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")

    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/login")

    template = env.get_template("job_analysis.html")
    
    # Check if AI is configured
    ai_settings = await ai_service.get_user_settings(user_id)
    ai_configured = bool(ai_settings and ai_settings.get("provider") and ai_settings.get("model"))
    
    return HTMLResponse(content=template.render(
        user_name=user.name,
        user_email=user.email,
        active_page="jobs",
        page_title="Jobs",
        page_subtitle="Analyze fit, rehearse interviews, and tailor your narrative for every role.",
        ai_configured=ai_configured
    ))


@router.get("/api/jobs/{job_id}/analysis")
async def get_job_analysis(request: Request, job_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    analysis = await job_analysis_service.get_analysis(job_id, user_id)
    if not analysis:
        return JSONResponse(content={"analyzed": False})
    
    return analysis


@router.post("/api/jobs/{job_id}/analyze")
async def analyze_job(request: Request, job_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check AI config
    ai_settings = await ai_service.get_user_settings(user_id)
    if not ai_settings or not ai_settings.get("provider") or not ai_settings.get("model"):
        raise HTTPException(status_code=400, detail="AI not configured")
        
    try:
        analysis = await job_analysis_service.generate_analysis(job_id, user_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/jobs/{job_id}/mock_sessions")
async def get_job_mock_sessions(request: Request, job_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sessions = await mock_service.list_sessions(user_id, job_id)
    return sessions


@router.get("/api/jobs")
async def list_jobs(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await job_service.list_jobs(user_id)


@router.post("/api/jobs")
async def create_job(request: Request, data: JobPostCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await job_service.create_job(user_id, data)


@router.put("/api/jobs/{job_id}")
async def update_job(request: Request, job_id: int, data: JobPostCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await job_service.update_job(job_id, user_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True}


@router.delete("/api/jobs/{job_id}")
async def delete_job(request: Request, job_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await job_service.delete_job(job_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"success": True}


@router.get("/profile")
async def profile_page(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/login")

    profile = await profile_service.get_profile(user_id)
    if not profile:
        profile = UserProfile(
            id=user.id or 0,
            name=user.name,
            email=user.email,
            title=user.title or "",
            summary="",
            location="",
            years_of_experience=0,
            date_of_birth=user.date_of_birth,
            phone=user.phone,
            website=user.website,
            linkedin=user.linkedin,
            github=user.github,
            work_experience=[],
            education=[],
            certifications=[],
            courses=[],
            achievements=[],
            skills=[],
            projects=[]
        )
    profile_age = calculate_age(profile.date_of_birth)
    profile_completeness = calculate_profile_completeness(profile)
    behavioral_profile = await behavioral_service.get_profile(user_id)
    can_retake_behavioral = True
    if behavioral_profile:
        # Check if updated_at is more than 6 months ago
        months_diff = (datetime.now() - behavioral_profile.updated_at).days / 30
        can_retake_behavioral = months_diff >= 6
    
    template = env.get_template("profile.html")
    return HTMLResponse(content=template.render(
        user_name=profile.name,
        user_email=profile.email,
        user_title=profile.title or "Professional",
        active_page="profile",
        page_title="Profile Overview",
        page_subtitle="Your unified career narrative",
        profile=profile,
        profile_age=profile_age,
        profile_completeness=profile_completeness,
        behavioral_profile=behavioral_profile,
        can_retake_behavioral=can_retake_behavioral
    ))


@router.get("/profile/curriculum")
async def curriculum_page(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/login")
    
    template = env.get_template("curriculum.html")
    return HTMLResponse(content=template.render(
        user_name=user.name,
        user_email=user.email,
        user_title=user.title or "Professional",
        active_page="profile"
    ))


@router.get("/api/profile")
async def get_profile(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    profile = await profile_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/api/profile/basic")
async def update_basic(request: Request, basic: ProfileBasic):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_basic(user_id, basic)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.get("/api/profile/experience")
async def get_experience(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.get_work_experience(user_id)


@router.post("/api/profile/experience")
async def create_experience(request: Request, data: WorkExperienceCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.create_work_experience(user_id, data)


@router.put("/api/profile/experience/{exp_id}")
async def update_experience(request: Request, exp_id: int, data: WorkExperienceCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_work_experience(exp_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Experience not found")
    return result


@router.delete("/api/profile/experience/{exp_id}")
async def delete_experience(request: Request, exp_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await profile_service.delete_work_experience(exp_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Experience not found")
    return {"success": True}


@router.get("/api/profile/education")
async def get_education(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.get_education(user_id)


@router.post("/api/profile/education")
async def create_education(request: Request, data: EducationCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.create_education(user_id, data)


@router.put("/api/profile/education/{edu_id}")
async def update_education(request: Request, edu_id: int, data: EducationCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_education(edu_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Education not found")
    return result


@router.delete("/api/profile/education/{edu_id}")
async def delete_education(request: Request, edu_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await profile_service.delete_education(edu_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Education not found")
    return {"success": True}


@router.get("/api/profile/certifications")
async def get_certifications(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.get_certifications(user_id)


@router.post("/api/profile/certifications")
async def create_certification(request: Request, data: CertificationCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.create_certification(user_id, data)


@router.put("/api/profile/certifications/{cert_id}")
async def update_certification(request: Request, cert_id: int, data: CertificationCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_certification(cert_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Certification not found")
    return result


@router.delete("/api/profile/certifications/{cert_id}")
async def delete_certification(request: Request, cert_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await profile_service.delete_certification(cert_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Certification not found")
    return {"success": True}


@router.get("/api/profile/courses")
async def get_courses(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.get_courses(user_id)


@router.post("/api/profile/courses")
async def create_course(request: Request, data: CourseCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.create_course(user_id, data)


@router.put("/api/profile/courses/{course_id}")
async def update_course(request: Request, course_id: int, data: CourseCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_course(course_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Course not found")
    return result


@router.delete("/api/profile/courses/{course_id}")
async def delete_course(request: Request, course_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await profile_service.delete_course(course_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"success": True}


@router.get("/api/profile/achievements")
async def get_achievements(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.get_achievements(user_id)


@router.post("/api/profile/achievements")
async def create_achievement(request: Request, data: AchievementCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.create_achievement(user_id, data)


@router.put("/api/profile/achievements/{ach_id}")
async def update_achievement(request: Request, ach_id: int, data: AchievementCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_achievement(ach_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return result


@router.delete("/api/profile/achievements/{ach_id}")
async def delete_achievement(request: Request, ach_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await profile_service.delete_achievement(ach_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Achievement not found")
    return {"success": True}


@router.get("/api/profile/skills")
async def get_skills(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.get_skills(user_id)


@router.post("/api/profile/skills")
async def create_skill(request: Request, data: SkillCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.create_skill(user_id, data)


@router.put("/api/profile/skills/{skill_id}")
async def update_skill(request: Request, skill_id: int, data: SkillCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_skill(skill_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Skill not found")
    return result


@router.delete("/api/profile/skills/{skill_id}")
async def delete_skill(request: Request, skill_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await profile_service.delete_skill(skill_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"success": True}


@router.get("/api/profile/projects")
async def get_projects(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.get_projects(user_id)


@router.post("/api/profile/projects")
async def create_project(request: Request, data: ProjectCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await profile_service.create_project(user_id, data)


@router.put("/api/profile/projects/{proj_id}")
async def update_project(request: Request, proj_id: int, data: ProjectCreate):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await profile_service.update_project(proj_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.delete("/api/profile/projects/{proj_id}")
async def delete_project(request: Request, proj_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await profile_service.delete_project(proj_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}


@router.get("/jobs/{job_id}/mock-setup")
async def mock_setup_page(request: Request, job_id: int):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = await user_service.get_user(user_id)
    job = await job_service.get_job(job_id, user_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")
        
    ai_settings = await ai_service.get_user_settings(user_id)
    ai_configured = bool(ai_settings and ai_settings.get("provider") and ai_settings.get("model"))
    # STT is always "available" because we support browser STT as a fallback
    stt_available = True 
    
    template = env.get_template("mock_interview_setup.html")
    return HTMLResponse(content=template.render(
        user_id=user_id,
        user_name=user.name,
        user_email=user.email,
        job=job,
        ai_configured=ai_configured,
        stt_available=stt_available,
        ai_settings_json=JSONResponse(ai_settings).body.decode() if ai_settings else 'null',
        languages=LANGUAGES,
        active_page="jobs"
    ))


@router.get("/jobs/interview/{session_id}")
async def interview_report_page(request: Request, session_id: int):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = await user_service.get_user(user_id)
    session = await mock_service.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    answers = await mock_service.get_answers(session_id)
    job = await job_service.get_job(session["job_id"], user_id)
    
    template = env.get_template("mock_interview_report.html")
    return HTMLResponse(content=template.render(
        user_name=user.name,
        session=session,
        answers=answers,
        job=job,
        active_page="jobs"
    ))


@router.get("/jobs/mock/{session_id}")
async def mock_session_page(request: Request, session_id: int):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = await user_service.get_user(user_id)
    session = await mock_service.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    job = await job_service.get_job(session["job_id"], user_id)
    
    template = env.get_template("mock_interview_session.html")
    return HTMLResponse(content=template.render(
        user_id=user_id,
        user_name=user.name,
        session=session,
        job=job,
        active_page="jobs"
    ))


# --- Mock Interview API Routes ---

@router.post("/api/mock/start")
async def start_mock_session(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json()
    try:
        session = await mock_service.start_session(user_id, body)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mock/{session_id}/answer")
async def submit_mock_answer(request: Request, session_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json()
    try:
        evaluation = await mock_service.evaluate_answer(
            user_id=user_id,
            session_id=session_id,
            question_index=body["question_index"],
            user_answer=body["user_answer"],
            time_taken=body.get("time_taken")
        )
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mock/{session_id}/follow-up")
async def submit_follow_up(request: Request, session_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json()
    try:
        evaluation = await mock_service.evaluate_follow_up(
            user_id=user_id,
            session_id=session_id,
            question_index=body["question_index"],
            follow_up_answer=body["follow_up_answer"]
        )
        return evaluation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mock/{session_id}/finish")
async def finish_mock_session(request: Request, session_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await mock_service.finish_session(user_id, session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/mock/{session_id}")
async def get_mock_session(request: Request, session_id: int):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await mock_service.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    answers = await mock_service.get_answers(session_id)
    return {"session": session, "answers": answers}