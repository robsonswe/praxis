from pathlib import Path
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.services.message import MessageService
from app.services.chat_session import ChatSessionService
from app.services.user import UserService
from app.services.ai_service import AIService
from app.repositories.message import MessageRepository
from app.repositories.chat_session import ChatSessionRepository
from app.repositories.user import UserRepository
from app.database import init_db, set_db_path, close_connection
from app.controllers.profile import get_current_user

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent
env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(['html', 'xml'])
)

ai_service = AIService()
user_repo = UserRepository()
user_service = UserService(user_repo)


async def get_services():
    msg_repo = MessageRepository()
    await msg_repo.initialize()
    msg_service = MessageService(msg_repo)
    
    sess_repo = ChatSessionRepository()
    await sess_repo.initialize()
    sess_service = ChatSessionService(sess_repo)
    
    return msg_service, sess_service


@router.get("/chat")
async def chat_page(request: Request, session: int | None = None):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/setup")
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        return RedirectResponse(url="/setup")
    
    msg_service, sess_service = await get_services()
    sessions = await sess_service.get_user_sessions(user_id)
    
    template = env.get_template("chat.html")
    html = template.render(
        user=user.to_dict(),
        sessions=[s.to_dict() for s in sessions],
        active_session_id=session
    )
    return HTMLResponse(content=html)


@router.get("/chat/{session_id}/messages")
async def get_messages(session_id: int, request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    msg_service, sess_service = await get_services()
    messages = await msg_service.get_session_messages(session_id)
    return JSONResponse(content=[m.to_dict() for m in messages])


@router.get("/chat/{session_id}/sessions")
async def get_sessions(session_id: int, request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    msg_service, sess_service = await get_services()
    sessions = await sess_service.get_user_sessions(user_id)
    return JSONResponse(content=[s.to_dict() for s in sessions])


@router.post("/chat/session")
async def create_session(request: Request, title: str = Form(default="Untitled Chat")):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/setup")
    
    msg_service, sess_service = await get_services()
    session = await sess_service.create_session(user_id, title)
    return JSONResponse(content={"id": session.id, "title": session.title})


@router.post("/chat/session/init")
async def init_session(request: Request, first_message: str = Form()):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401)
        
    msg_service, sess_service = await get_services()
    
    # Generate title in parallel (well, sequentially here but we could optimize)
    await ai_service.initialize()
    title = await ai_service.generate_title(user_id, user.name, first_message)
    
    session = await sess_service.create_session(user_id, title)
    return JSONResponse(content={"id": session.id, "title": session.title})


@router.patch("/chat/session/{session_id}/title")
async def update_title(session_id: int, request: Request, title: str = Form()):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    msg_service, sess_service = await get_services()
    await sess_service.update_session_title(session_id, title)
    return JSONResponse(content={"status": "ok", "title": title})


@router.get("/chat/stream")
async def stream_chat(request: Request, session_id: int, message: str):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401)
    
    msg_service, sess_service = await get_services()
    
    # Save user message
    await msg_service.add_user_message(session_id, message)
    
    # Get context
    session_messages = await msg_service.get_session_messages(session_id)
    ai_messages = [{"role": m.role, "content": m.content} for m in session_messages]
    
    async def event_generator():
        full_content = ""
        await ai_service.initialize()
        
        try:
            async for chunk in ai_service.send_message_streaming(user_id, user.name, session_id, ai_messages):
                if chunk.startswith("Error:"):
                    yield f"data: {json.dumps({'error': chunk[6:].strip()})}\n\n"
                    return
                
                full_content += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # Save final response
            if full_content:
                await msg_service.add_assistant_message(session_id, full_content)
                yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat")
async def send_message(request: Request, message: str = Form(), session_id: int = Form()):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await user_repo.initialize()
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401)
        
    msg_service, sess_service = await get_services()
    
    # Save user message
    user_msg = await msg_service.add_user_message(session_id, message)
    
    # Get all messages for this session to build context
    session_messages = await msg_service.get_session_messages(session_id)
    
    # Convert to AI format
    ai_messages = [
        {"role": m.role, "content": m.content}
        for m in session_messages
    ]
    
    # Call AI service
    await ai_service.initialize()
    ai_response = await ai_service.send_message(user_id, user.name, session_id, ai_messages)
    
    if "error" in ai_response:
        return JSONResponse(content={
            "user_message": user_msg.to_dict(),
            "error": ai_response["error"]
        })
    
    # Save AI response
    assistant_msg = await msg_service.add_assistant_message(
        session_id, 
        ai_response["content"]
    )
    
    return JSONResponse(content={
        "user_message": user_msg.to_dict(),
        "assistant_message": assistant_msg.to_dict()
    })


@router.delete("/chat/session/{session_id}")
async def delete_session(session_id: int, request: Request):
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(status_code=401)
    
    msg_service, sess_service = await get_services()
    await sess_service.delete_session(session_id)
    return JSONResponse(content={"status": "deleted"})