from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


def require_login(request: Request):
    """Ensure the current session is authenticated.

    The dependency checks for ``user_id`` in the session. When absent it
    either redirects HTML clients to the login page or raises an HTTP 401
    error for API requests.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            raise HTTPException(status_code=303, headers={"Location": "/login"})
        raise HTTPException(status_code=401)
    return None


def require_admin(request: Request):
    """Ensure the current session belongs to an admin user."""
    # First confirm the user is logged in.
    require_login(request)

    # Import locally to avoid circular imports during application start-up.
    from models import SessionLocal, User

    db = SessionLocal()
    try:
        user_id = request.session.get("user_id")
        user = db.get(User, user_id)
        if not user or not user.is_admin:
            raise HTTPException(status_code=403)
    finally:
        db.close()
    return None


class RememberMeMiddleware(BaseHTTPMiddleware):
    """Populate sessions based on persistent remember-me tokens."""

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("session_token")
        invalid_token = False
        if token:
            from models import RememberToken, SessionLocal, User

            db = SessionLocal()
            try:
                record = db.query(RememberToken).filter_by(token=token).first()
                if record:
                    if not request.session.get("user_id"):
                        user = db.get(User, record.user_id)
                        if user:
                            request.session["user_id"] = user.id
                            request.session["username"] = user.username
                            request.session["is_admin"] = user.is_admin
                            request.session["full_name"] = (
                                f"{user.first_name or ''} {user.last_name or ''}".strip()
                            )
                        else:
                            db.delete(record)
                            db.commit()
                            invalid_token = True
                else:
                    invalid_token = True
                    request.session.clear()
            finally:
                db.close()
        response = await call_next(request)
        if invalid_token:
            response.delete_cookie("session_token")
        return response
