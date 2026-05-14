from fastapi import APIRouter, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from datetime import datetime
from typing import List
from app.services.behavioral import BehavioralService
from app.models.behavioral import BehavioralResponse, BehavioralAssessment
from app.repositories.user import UserRepository
from app.services.user import UserService

router = APIRouter(prefix="/behavioral", tags=["behavioral"])
BASE_DIR = Path(__file__).parent.parent
env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(['html', 'xml'])
)
behavioral_service = BehavioralService()
user_repo = UserRepository()
user_service = UserService(user_repo)

def get_current_user(request: Request) -> int | None:
    user_id = request.cookies.get("user_id")
    if user_id:
        return int(user_id)
    return None

@router.get("/", response_class=HTMLResponse)
async def get_behavioral_page(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")
    
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/setup")
    
    profile = await behavioral_service.get_profile(user_id)
    if profile:
        months_diff = (datetime.now() - profile.updated_at).days / 30
        if months_diff < 6:
            return RedirectResponse(url="/profile", status_code=303)
    
    questions = behavioral_service.questions
    existing_responses = await behavioral_service.get_responses(user_id)
    
    template = env.get_template("behavioral.html")
    return HTMLResponse(content=template.render(
        request=request,
        questions=questions,
        responses=existing_responses,
        user_name=user.name,
        active_page="behavioral"
    ))

@router.post("/submit")
async def submit_behavioral(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/login")

    # Enforce 6-month rule
    profile = await behavioral_service.get_profile(user_id)
    if profile:
        months_diff = (datetime.now() - profile.updated_at).days / 30
        if months_diff < 6:
            return RedirectResponse(url="/profile", status_code=303)

    form_data = await request.form()
    responses = []
    
    for key, value in form_data.items():
        if key.startswith("q_"):
            q_id = int(key.split("_")[1])
            responses.append(BehavioralResponse(question_id=q_id, selected_option=value))
    
    if responses:
        await behavioral_service.save_responses(user_id, responses)
        
    return RedirectResponse(url="/profile", status_code=303)

@router.get("/results")
async def get_results(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return {"error": "Not authenticated"}

    profile = await behavioral_service.get_profile(user_id)
    if not profile:
        return {"error": "No behavioral profile found"}
    return profile
