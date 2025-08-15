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
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
):
    """Verify user credentials and establish a session."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and pwd_context.verify(password, user.password):
            request.session["user_id"] = user.id
            request.session["username"] = user.username
            request.session["is_admin"] = user.is_admin
            request.session["full_name"] = (
                f"{user.first_name or ''} {user.last_name or ''}".strip()
            )
            response = RedirectResponse("/", status_code=303)
            if remember:
                max_age = 60 * 60 * 24 * 30  # 30 days
                response.set_cookie("username", username, max_age=max_age)
                response.set_cookie("password", password, max_age=max_age)
            else:
                response.delete_cookie("username")
                response.delete_cookie("password")
            return response
    finally:
        db.close()
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid credentials"},
        status_code=401,
    )


@router.get("/logout")
@router.post("/logout")
def logout(request: Request):
    """Clear the current session."""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


__all__ = ["router"]
