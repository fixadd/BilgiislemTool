"""Authentication routes."""

import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect

from models import SessionLocal, User, pwd_context
from utils import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, csrf_protect: CsrfProtect = Depends()) -> HTMLResponse:
    """Render the login form."""
    token, signed = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        request, "login.html", {"csrf_token": token}
    )
    csrf_protect.set_csrf_cookie(signed, response)
    return response


@router.post("/login")
async def login(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    username: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
):
    """Verify user credentials and establish a session."""
    await csrf_protect.validate_csrf(request)
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
                token = secrets.token_urlsafe(16)
                request.session["session_token"] = token
                response.set_cookie(
                    "session_token",
                    token,
                    max_age=max_age,
                    httponly=True,
                    samesite="lax",
                )
            else:
                response.delete_cookie("username")
                response.delete_cookie("session_token")
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
async def logout(
    request: Request, csrf_protect: CsrfProtect = Depends()
):
    """Clear the current session."""
    if request.method == "POST":
        await csrf_protect.validate_csrf(request)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


__all__ = ["router"]
