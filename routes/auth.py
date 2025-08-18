"""Authentication routes."""

import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.orm import Session

from models import RememberToken, User, get_db, pwd_context
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
    db: Session = Depends(get_db),
):
    """Verify user credentials and establish a session."""
    await csrf_protect.validate_csrf(request)
    user = db.query(User).filter(User.username == username).first()
    if user and pwd_context.verify(password, user.password):
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["is_admin"] = user.is_admin
        request.session["full_name"] = (
            f"{user.first_name or ''} {user.last_name or ''}".strip()
        )
        response = RedirectResponse("/", status_code=303)
        db.query(RememberToken).filter(
            RememberToken.user_id == user.id
        ).delete()
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
            db.add(RememberToken(user_id=user.id, token=token))
        else:
            response.delete_cookie("username")
            response.delete_cookie("session_token")
        db.commit()
        return response
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid credentials"},
        status_code=401,
    )


@router.get("/logout")
@router.post("/logout")
async def logout(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    db: Session = Depends(get_db),
):
    """Clear the current session."""
    if request.method == "POST":
        await csrf_protect.validate_csrf(request)
    token = request.cookies.get("session_token")
    if token:
        db.query(RememberToken).filter(RememberToken.token == token).delete()
        db.commit()
    request.session.clear()
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session_token")
    response.delete_cookie("username")
    return response


__all__ = ["router"]
