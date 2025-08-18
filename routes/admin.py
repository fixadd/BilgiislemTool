"""Admin management routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import User, get_db, pwd_context
from utils import templates
from utils.auth import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """List all users."""
    params = request.query_params
    q = params.get("q", "")
    query = db.query(User)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                User.username.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    users = query.all()
    return templates.TemplateResponse(request, "admin.html", {"users": users, "q": q})


@router.post("/admin/create")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(None),
    last_name: str = Form(None),
    email: str = Form(None),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Create a new user."""
    if db.query(User).filter(User.username == username).first():
        users = db.query(User).all()
        return templates.TemplateResponse(
            request,
            "admin.html",
            {"users": users, "error": "Kullanıcı mevcut", "q": ""},
            status_code=400,
        )
    user = User(
        username=username,
        password=pwd_context.hash(password),
        is_admin=is_admin,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/make_admin/{user_id}")
def make_admin(user_id: int, db: Session = Depends(get_db)):
    """Promote a user to admin."""
    user = db.get(User, user_id)
    if user:
        user.is_admin = True
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.get("/admin/edit/{user_id}", response_class=HTMLResponse)
def edit_user_form(
    request: Request, user_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Render the edit form for a user."""
    target = db.get(User, user_id)
    if not target:
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(
        request, "admin_edit.html", {"target": target}
    )


@router.post("/admin/edit/{user_id}")
def edit_user(
    user_id: int,
    password: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),
    email: str = Form(None),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Update a user's details."""
    user = db.get(User, user_id)
    if user:
        if password:
            user.password = pwd_context.hash(password)
            user.must_change_password = True
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_admin = is_admin
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/delete/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user."""
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


__all__ = ["router"]
