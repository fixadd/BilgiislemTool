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
