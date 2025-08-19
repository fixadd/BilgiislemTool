import os
import secrets
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic_settings import BaseSettings

from models import init_db, init_admin, SessionLocal
from routes import router as api_router
from utils import cleanup_deleted
from utils.auth import RememberMeMiddleware

secret_key = os.getenv("SESSION_SECRET")
if not secret_key:
    secret_key = secrets.token_hex(32)
    logging.warning(
        "SESSION_SECRET environment variable is not set. Generated a random secret key; "
        "sessions will reset on application restart."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and default admin user on startup."""
    init_db()
    init_admin()
    db = SessionLocal()
    try:
        cleanup_deleted(db)
    finally:
        db.close()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(RememberMeMiddleware)
app.add_middleware(SessionMiddleware, secret_key=secret_key)
app.mount("/image", StaticFiles(directory="image"), name="image")
app.mount("/static", StaticFiles(directory="static"), name="static")


class CsrfSettings(BaseSettings):
    secret_key: str = secret_key
    token_key: str = "csrf_token"
    token_location: str = "body"
    cookie_samesite: str | None = "lax"


@CsrfProtect.load_config
def load_csrf_config() -> CsrfSettings:
    return CsrfSettings()


@app.exception_handler(CsrfProtectError)
def csrf_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

# Register API routes
app.include_router(api_router)
