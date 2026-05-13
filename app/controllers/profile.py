from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.services.user import UserService
from app.repositories.user import UserRepository
from app.database import init_db, get_connection, close_connection

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(['html', 'xml'])
)

user_repo = UserRepository()
user_service = UserService(user_repo)


@router.get("/setup")
async def setup_page():
    template = env.get_template("setup.html")
    return HTMLResponse(content=template.render())


@router.post("/setup")
async def create_profile(username: str = Form(), email: str = Form()):
    await user_repo.initialize()
    
    # Check if email exists
    existing = await user_service.get_by_email(email)
    if existing:
        template = env.get_template("setup.html")
        return HTMLResponse(content=template.render(error="Email already registered"))
        
    user = await user_service.create_user(username, email)
    
    response = RedirectResponse(url="/chat", status_code=303)
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
        
    response = RedirectResponse(url="/chat", status_code=303)
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
    if user_id:
        await user_repo.initialize()
        user = await user_service.get_user(user_id)
        if user:
            return RedirectResponse(url="/chat")
    return RedirectResponse(url="/login")