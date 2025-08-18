from fastapi import HTTPException, Request


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
