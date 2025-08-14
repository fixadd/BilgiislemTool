"""Authentication and user account related endpoints."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import require_login
from models import SessionLocal, User, pwd_context
from utils import templates


router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    """Render the login page."""

    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Basic form-based login."""

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and pwd_context.verify(password, user.password):
            request.session["user"] = user.username
            return RedirectResponse("/", status_code=303)
    finally:
        db.close()
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid credentials"},
        status_code=401,
    )


@router.get("/logout")
def logout(request: Request):
    """Log the user out and redirect to the login page."""

    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request) -> HTMLResponse:
    """Render a simple profile page."""

    if redirect := require_login(request):
        return redirect
    user = {"first_name": "", "last_name": "", "email": ""}
    return templates.TemplateResponse(request, "profile.html", {"user": user})


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request) -> HTMLResponse:
    """Render the change password page."""

    if redirect := require_login(request):
        return redirect
    return templates.TemplateResponse(request, "change_password.html")


__all__ = ["router"]

