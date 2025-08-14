from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from models import init_db, init_admin, SessionLocal
from routes import router as api_router
from utils import cleanup_deleted

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")
app.mount("/image", StaticFiles(directory="image"), name="image")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    """Initialize database tables and default admin user on startup."""
    init_db()
    init_admin()
    db = SessionLocal()
    try:
        cleanup_deleted(db)
    finally:
        db.close()


# Register API routes
app.include_router(api_router)
