from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from models import init_db, init_admin
from routes import router

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")
app.mount("/image", StaticFiles(directory="image"), name="image")

# Initialize database and default admin user
init_db()
init_admin()

# Register API routes
app.include_router(router)
