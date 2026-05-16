from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.controllers.profile import router as profile_router
from app.controllers.chat import router as chat_router
from app.controllers.ai import router as ai_router
from app.controllers.behavioral import router as behavioral_router
from app.database import init_db, close_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_connection()


app = FastAPI(lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(profile_router)
app.include_router(chat_router)
app.include_router(ai_router)
app.include_router(behavioral_router)