"""Authentication routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from models import SessionLocal, User, pwd_context
from utils import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> HTMLResponse:
    """Render the login form."""
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Verify user credentials and establish a session."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and pwd_context.verify(password, user.password):
            request.session["user_id"] = user.id
            return RedirectResponse("/", status_code=303)
    finally:
        db.close()
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid credentials"},
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request):
    """Clear the current session."""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


__all__ = ["router"]
