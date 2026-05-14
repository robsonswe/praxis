from pathlib import Path
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.services.user import UserService
from app.repositories.user import UserRepository
from app.repositories.profile import ProfileRepository
from app.services.profile import ProfileService
from app.models.profile import (
    ProfileBasic, WorkExperienceCreate, EducationCreate, CertificationCreate,
    CourseCreate, AchievementCreate, SkillCreate, ProjectCreate
)
from app.database import init_db, get_connection, close_connection

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(['html', 'xml'])
)

user_repo = UserRepository()
user_service = UserService(user_repo)

profile_repo = ProfileRepository()
profile_service = ProfileService(profile_repo)


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


@router.get("/")
async def root(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/login")
    
    template = env.get_template("index.html")
    return HTMLResponse(content=template.render(
        user_name=user.name,
        user_email=user.email,
        active_page="dashboard",
        page_title="Dashboard",
        page_subtitle="Your career preparation overview"
    ))


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.set_cookie("user_id", "", expires=0)
    return response


@router.get("/profile")
async def profile_page(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/login")
    
    template = env.get_template("profile.html")
    return HTMLResponse(content=template.render(
        user_name=user.name,
        user_email=user.email,
        user_title=user.title or "Professional",
        active_page="profile",
        page_title="Profile Overview",
        page_subtitle="Your unified career narrative"
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